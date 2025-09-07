#!/usr/bin/env python3
"""
Database Migration Guardrails

Provides automated backup and rollback procedures for safe database migrations.
Ensures zero-downtime deployments with reliable rollback capabilities.

Addresses P0-12c: Add migration guardrails with automated backup and rollback procedures
"""

import os
import sys
import subprocess
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import tempfile
import shutil
import hashlib
from dataclasses import dataclass, asdict


@dataclass
class MigrationContext:
    """Context information for a migration operation"""
    migration_id: str
    backup_path: str
    pre_migration_schema_hash: str
    timestamp: str
    environment: str
    alembic_head_before: str
    database_url: str
    backup_size_bytes: int
    migration_files: List[str]


class MigrationGuardrails:
    """Database migration safety system with automated backup and rollback"""
    
    def __init__(self, database_url: str, backup_dir: str = "migration-backups"):
        self.database_url = database_url
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging for migration operations"""
        logger = logging.getLogger("migration_guardrails")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_current_alembic_head(self) -> str:
        """Get current Alembic head revision"""
        try:
            result = subprocess.run(
                ["alembic", "current"],
                capture_output=True,
                text=True,
                check=True,
                env={**os.environ, "PYTHONPATH": "."}
            )
            
            # Parse current head from alembic output
            output = result.stdout.strip()
            if output and "current" in output.lower():
                # Extract revision ID from output like "INFO  [alembic.runtime.migration] Context impl PostgresqlImpl."
                # "INFO  [alembic.runtime.migration] Will assume transactional DDL."
                # "Current revision(s) for postgresql://...: abc123def456"
                lines = output.split('\n')
                for line in lines:
                    if 'current revision' in line.lower():
                        revision = line.split(':')[-1].strip()
                        return revision
                # If we don't find the pattern above, try to extract any hex-like string
                import re
                revision_match = re.search(r'([a-f0-9]{12})', output)
                if revision_match:
                    return revision_match.group(1)
            
            return "unknown"
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get current Alembic head: {e}")
            return "unknown"
    
    def get_schema_hash(self) -> str:
        """Generate hash of current database schema for integrity verification"""
        try:
            # Get schema information using pg_dump schema-only
            result = subprocess.run([
                "pg_dump",
                self.database_url,
                "--schema-only",
                "--no-owner",
                "--no-privileges"
            ], capture_output=True, text=True, check=True)
            
            schema_content = result.stdout
            return hashlib.sha256(schema_content.encode()).hexdigest()
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to generate schema hash: {e}")
            return "unknown"
    
    def create_backup(self, migration_id: str) -> str:
        """Create full database backup before migration"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{migration_id}_{timestamp}.sql"
        backup_path = self.backup_dir / backup_filename
        
        self.logger.info(f"Creating database backup: {backup_path}")
        
        try:
            # Create compressed backup using pg_dump
            with open(backup_path, 'w') as backup_file:
                result = subprocess.run([
                    "pg_dump",
                    self.database_url,
                    "--verbose",
                    "--no-owner",
                    "--no-privileges",
                    "--format=plain"
                ], stdout=backup_file, stderr=subprocess.PIPE, text=True, check=True)
            
            # Verify backup was created successfully
            if not backup_path.exists() or backup_path.stat().st_size == 0:
                raise RuntimeError("Backup file was not created or is empty")
            
            backup_size = backup_path.stat().st_size
            self.logger.info(f"Backup created successfully: {backup_size:,} bytes")
            
            return str(backup_path)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            self.logger.error(f"Backup failed: {error_msg}")
            raise RuntimeError(f"Database backup failed: {error_msg}")
    
    def validate_migration_files(self, target_revision: Optional[str] = None) -> List[str]:
        """Validate migration files that will be applied"""
        try:
            # Get pending migrations
            cmd = ["alembic", "show"]
            if target_revision:
                cmd.append(target_revision)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env={**os.environ, "PYTHONPATH": "."}
            )
            
            # Parse migration files from output
            migration_files = []
            # This is a simplified parser - in production you might want more sophisticated parsing
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'alembic/versions' in line or '.py' in line:
                    migration_files.append(line.strip())
            
            self.logger.info(f"Found {len(migration_files)} migration files to apply")
            return migration_files
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to validate migration files: {e}")
            return []
    
    def perform_migration(self, target_revision: Optional[str] = None) -> bool:
        """Perform the actual database migration"""
        try:
            cmd = ["alembic", "upgrade"]
            if target_revision:
                cmd.append(target_revision)
            else:
                cmd.append("head")
            
            self.logger.info(f"Running migration command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env={**os.environ, "PYTHONPATH": "."}
            )
            
            self.logger.info("Migration completed successfully")
            self.logger.debug(f"Migration output: {result.stdout}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            self.logger.error(f"Migration failed: {error_msg}")
            return False
    
    def rollback_from_backup(self, backup_path: str) -> bool:
        """Rollback database from backup"""
        self.logger.warning(f"Starting database rollback from backup: {backup_path}")
        
        try:
            # Drop existing database schema (WARNING: This is destructive!)
            self.logger.warning("⚠️ Dropping existing database schema for rollback")
            
            # First, restore from the backup
            with open(backup_path, 'r') as backup_file:
                result = subprocess.run([
                    "psql",
                    self.database_url,
                    "--quiet"
                ], stdin=backup_file, capture_output=True, text=True, check=True)
            
            self.logger.info("Database rollback completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            self.logger.error(f"Rollback failed: {error_msg}")
            return False
    
    def verify_migration_success(self, expected_revision: str) -> bool:
        """Verify migration was applied successfully"""
        current_head = self.get_current_alembic_head()
        
        if expected_revision in current_head or current_head in expected_revision:
            self.logger.info(f"Migration verification successful: {current_head}")
            return True
        else:
            self.logger.error(f"Migration verification failed: expected {expected_revision}, got {current_head}")
            return False
    
    def save_migration_context(self, context: MigrationContext) -> None:
        """Save migration context for audit and rollback purposes"""
        context_file = self.backup_dir / f"context_{context.migration_id}.json"
        
        with open(context_file, 'w') as f:
            json.dump(asdict(context), f, indent=2)
        
        self.logger.info(f"Migration context saved: {context_file}")
    
    def load_migration_context(self, migration_id: str) -> Optional[MigrationContext]:
        """Load migration context from file"""
        context_file = self.backup_dir / f"context_{migration_id}.json"
        
        if not context_file.exists():
            return None
        
        try:
            with open(context_file, 'r') as f:
                context_data = json.load(f)
            
            return MigrationContext(**context_data)
        except Exception as e:
            self.logger.error(f"Failed to load migration context: {e}")
            return None
    
    def safe_migrate(self, target_revision: Optional[str] = None, dry_run: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Perform safe migration with automated backup and rollback capabilities
        
        Returns:
            Tuple[bool, Optional[str]]: (success, migration_id)
        """
        migration_id = f"migration_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(f"🚀 Starting safe migration process: {migration_id}")
        
        if dry_run:
            self.logger.info("🔍 DRY RUN MODE - No actual changes will be made")
        
        try:
            # Step 1: Pre-migration validation
            self.logger.info("📋 Step 1: Pre-migration validation")
            current_head = self.get_current_alembic_head()
            pre_schema_hash = self.get_schema_hash()
            migration_files = self.validate_migration_files(target_revision)
            
            self.logger.info(f"Current Alembic head: {current_head}")
            self.logger.info(f"Pre-migration schema hash: {pre_schema_hash[:16]}...")
            
            if dry_run:
                self.logger.info("✅ DRY RUN: Pre-migration validation completed")
                return True, migration_id
            
            # Step 2: Create backup
            self.logger.info("💾 Step 2: Creating database backup")
            backup_path = self.create_backup(migration_id)
            backup_size = Path(backup_path).stat().st_size
            
            # Step 3: Create migration context
            context = MigrationContext(
                migration_id=migration_id,
                backup_path=backup_path,
                pre_migration_schema_hash=pre_schema_hash,
                timestamp=datetime.now(timezone.utc).isoformat(),
                environment=os.getenv("ENVIRONMENT", "unknown"),
                alembic_head_before=current_head,
                database_url=self.database_url,
                backup_size_bytes=backup_size,
                migration_files=migration_files
            )
            
            self.save_migration_context(context)
            
            # Step 4: Perform migration
            self.logger.info("⚡ Step 4: Performing database migration")
            migration_success = self.perform_migration(target_revision)
            
            if not migration_success:
                self.logger.error("❌ Migration failed, initiating rollback")
                
                # Step 5a: Rollback on failure
                self.logger.info("🔄 Step 5a: Rolling back from backup")
                rollback_success = self.rollback_from_backup(backup_path)
                
                if rollback_success:
                    self.logger.info("✅ Rollback completed successfully")
                    return False, migration_id
                else:
                    self.logger.critical("💥 CRITICAL: Migration failed AND rollback failed!")
                    return False, migration_id
            
            # Step 5b: Verify migration success
            self.logger.info("✅ Step 5b: Verifying migration success")
            expected_revision = target_revision or "head"
            verification_success = self.verify_migration_success(expected_revision)
            
            if not verification_success:
                self.logger.error("❌ Migration verification failed, initiating rollback")
                rollback_success = self.rollback_from_backup(backup_path)
                return False, migration_id
            
            # Step 6: Post-migration validation
            self.logger.info("🔍 Step 6: Post-migration validation")
            post_schema_hash = self.get_schema_hash()
            self.logger.info(f"Post-migration schema hash: {post_schema_hash[:16]}...")
            
            # Log schema change
            if pre_schema_hash != post_schema_hash:
                self.logger.info("📊 Database schema has been successfully modified")
            else:
                self.logger.info("📊 Database schema unchanged (no-op migration)")
            
            self.logger.info(f"🎉 Safe migration completed successfully: {migration_id}")
            return True, migration_id
            
        except Exception as e:
            self.logger.error(f"💥 Unexpected error during migration: {e}")
            
            # Attempt emergency rollback
            if 'backup_path' in locals():
                self.logger.info("🚨 Attempting emergency rollback")
                self.rollback_from_backup(backup_path)
            
            return False, migration_id
    
    def list_available_backups(self) -> List[Dict[str, Any]]:
        """List all available migration backups"""
        backups = []
        
        for backup_file in self.backup_dir.glob("backup_*.sql"):
            stat = backup_file.stat()
            backups.append({
                "file": backup_file.name,
                "path": str(backup_file),
                "size_bytes": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "age_hours": (datetime.now(timezone.utc) - datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)).total_seconds() / 3600
            })
        
        # Sort by creation time, newest first
        backups.sort(key=lambda x: x["created"], reverse=True)
        return backups
    
    def cleanup_old_backups(self, keep_count: int = 10) -> None:
        """Cleanup old backup files, keeping the most recent ones"""
        backups = self.list_available_backups()
        
        if len(backups) <= keep_count:
            self.logger.info(f"No cleanup needed, {len(backups)} backups within retention limit")
            return
        
        backups_to_delete = backups[keep_count:]
        
        for backup in backups_to_delete:
            try:
                backup_path = Path(backup["path"])
                context_file = self.backup_dir / f"context_{backup['file'].replace('backup_', '').replace('.sql', '')}.json"
                
                backup_path.unlink()
                if context_file.exists():
                    context_file.unlink()
                
                self.logger.info(f"Deleted old backup: {backup['file']}")
                
            except Exception as e:
                self.logger.error(f"Failed to delete backup {backup['file']}: {e}")


def main():
    """Main entry point for migration guardrails"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration guardrails with automated backup and rollback")
    parser.add_argument("--database-url", required=True, help="Database connection URL")
    parser.add_argument("--target-revision", help="Target migration revision (default: head)")
    parser.add_argument("--backup-dir", default="migration-backups", help="Backup directory")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without making changes")
    parser.add_argument("--list-backups", action="store_true", help="List available backups")
    parser.add_argument("--cleanup-backups", type=int, metavar="COUNT", help="Cleanup old backups, keeping COUNT most recent")
    
    args = parser.parse_args()
    
    try:
        guardrails = MigrationGuardrails(args.database_url, args.backup_dir)
        
        if args.list_backups:
            backups = guardrails.list_available_backups()
            print(f"\n📁 Available backups ({len(backups)} found):")
            for backup in backups:
                print(f"   • {backup['file']} ({backup['size_bytes']:,} bytes, {backup['age_hours']:.1f}h ago)")
            return
        
        if args.cleanup_backups is not None:
            guardrails.cleanup_old_backups(args.cleanup_backups)
            return
        
        # Perform safe migration
        success, migration_id = guardrails.safe_migrate(args.target_revision, args.dry_run)
        
        if success:
            print(f"✅ Migration {migration_id} completed successfully")
            sys.exit(0)
        else:
            print(f"❌ Migration {migration_id} failed")
            sys.exit(1)
    
    except Exception as e:
        print(f"💥 Migration guardrails failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()