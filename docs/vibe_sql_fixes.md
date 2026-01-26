# Vibe Server SQL Fixes

## Problem
The Vibe server's `vibe_check_db` tool generates SQL queries with UNION ALL that fail due to:
1. Mismatched column counts in UNION ALL statements
2. ORDER BY referencing non-existent columns
3. NULL handling issues

## Solution
Added `validate_union_all_query()` function that:
1. Detects problematic UNION ALL patterns
2. Fixes column mismatches with proper NULL aliases
3. Creates unified order_field for sorting
4. Uses NULLS LAST for proper NULL handling

## Usage
The function is automatically called when processing queries that match the problematic pattern.

## Testing
Run the test script to verify fixes:
```bash
python3 scripts/fix_vibe_sql.py
```
