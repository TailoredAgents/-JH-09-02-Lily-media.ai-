# Migration Chain Fix Plan - P0-1c Critical Issue

## Current Problems Identified

### 1. Multiple Root Migrations
- `000_baseline_existing_schema.py`: down_revision = None
- `001_initial_migration.py`: down_revision = None
**Fix**: Make baseline the single root, chain initial_migration after baseline

### 2. Duplicate Revision Numbers
- **001**: initial_migration vs add_core_missing_tables
- **017**: add_missing_user_columns vs add_public_uuid_columns  
- **018**: add_dead_letter_queue vs ensure_engagement_data
- **031**: usage_record_table vs webhook_reliability_improvements

### 3. Broken Chain References
- Migration 005 → '373835cefaf9' (should be '004_add_notifications')
- Migration 019 → 'f42f94c7a129' (should be sequential)
- Migration 022 → 'f42f94c7a129' (should be sequential)  
- Migration 023 → 'f42f94c7a129' (should be sequential)
- Migration 026 → '027_create_content_drafts_and_schedules' (circular)

### 4. Missing/Misnamed Revisions
- Error looking for '003_essential_tables' vs actual '003_enhanced_content_metadata'

## Systematic Fix Plan

### Phase 1: Establish Single Root Chain
1. Keep `000_baseline_existing_schema` as root (down_revision = None)
2. Remove `001_initial_migration.py` (duplicate functionality)
3. Rename `001_add_core_missing_tables` → `001_add_core_missing_tables` (keep as-is)

### Phase 2: Resolve Duplicate Numbers
1. **017 series**:
   - Keep: `017_add_missing_user_columns.py` 
   - Rename: `017_add_public_uuid_columns.py` → `018_add_public_uuid_columns.py`

2. **018 series** (after renaming above):
   - Keep: `018_add_dead_letter_queue.py` → `019_add_dead_letter_queue.py`  
   - Rename: `018_ensure_engagement_data_column.py` → `020_ensure_engagement_data_column.py`

3. **031 series**:
   - Keep: `031_add_usage_record_table.py`
   - Rename: `031_webhook_reliability_improvements.py` → `034_webhook_reliability_improvements.py`

### Phase 3: Fix Chain References
1. Fix circular reference: 026 → 027 (wrong direction)
2. Replace all 'f42f94c7a129' references with proper sequential IDs
3. Fix '373835cefaf9' reference in migration 005

### Phase 4: Renumber Sequence
Final sequential chain:
000 → 001 → 002 → 003 → 004 → 005 → 006 → 007 → 008 → 008a → 009 → ... → 033 → 034

## Implementation Steps
1. Create backup of migration files
2. Systematically rename and fix files
3. Update all down_revision references  
4. Test with `alembic current` and `alembic check`
5. Validate complete chain integrity