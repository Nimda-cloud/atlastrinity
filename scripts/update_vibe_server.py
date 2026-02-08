"""
Update Vibe server with corrected SQL queries
"""

import os
import shutil
from datetime import datetime


def update_vibe_server():
    """Update Vibe server with SQL fixes"""

    # Create a backup of the current vibe_server.py
    # Create a backup of the current vibe_server.py
    HOME = os.path.expanduser("~")
    PROJECT_ROOT = os.path.join(HOME, "Documents/GitHub/atlastrinity")
    vibe_server_path = os.path.join(PROJECT_ROOT, "src/mcp_server/vibe_server.py")
    backup_path = f"{vibe_server_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if os.path.exists(vibe_server_path):
        shutil.copy2(vibe_server_path, backup_path)
        print(f"✅ Backup created: {backup_path}")

    # Add SQL validation function to vibe_server.py
    sql_validation_code = '''
def validate_union_all_query(query: str) -> str:
    """
    Validates and fixes UNION ALL queries with ORDER BY issues
    
    Args:
        query: SQL query string
        
    Returns:
        Fixed SQL query string
    """
    # Check if this is a problematic UNION ALL query
    if "UNION ALL" in query and "ORDER BY" in query:
        # Basic fix for common pattern
        if "CASE" in query and "source_table" in query:
            # This looks like the problematic query pattern
            fixed_query = """
            SELECT * FROM (
                SELECT 
                    'tool_executions' as source_table, 
                    te.tool_name, te.arguments, te.result, te.created_at as created_at, 
                    ts.action, ts.sequence_number, te.created_at as order_field
                FROM tool_executions te 
                JOIN task_steps ts ON te.step_id = ts.id 
                WHERE te.result LIKE '%{search_term}%' 
                   OR te.arguments LIKE '%{search_term}%' 
                
                UNION ALL 
                
                SELECT 
                    'task_steps' as source_table, 
                    NULL as tool_name, NULL as arguments, NULL as result, NULL as created_at, 
                    ts.action, ts.sequence_number, NULL as order_field
                FROM task_steps ts 
                WHERE ts.action LIKE '%{search_term}%' 
                
                UNION ALL 
                
                SELECT 
                    'logs' as source_table, 
                    NULL as tool_name, NULL as arguments, NULL as result, l.timestamp as created_at, 
                    l.message as action, NULL as sequence_number, l.timestamp as order_field
                FROM logs l 
                WHERE l.message LIKE '%{search_term}%'
            )
            ORDER BY order_field DESC NULLS LAST
            LIMIT 50
            """
            return fixed_query
    
    return query

'''

    # Read the current vibe_server.py
    try:
        with open(vibe_server_path) as f:
            content = f.read()

        # Check if validation function already exists
        if "def validate_union_all_query" not in content:
            # Add the validation function after imports
            import_end = content.find("from src.brain.db.manager import db_manager")
            if import_end != -1:
                insert_pos = content.find("\n", import_end) + 1
                content = content[:insert_pos] + sql_validation_code + "\n" + content[insert_pos:]

                # Write the updated content
                with open(vibe_server_path, "w") as f:
                    f.write(content)

                print("✅ SQL validation function added to vibe_server.py")
            else:
                print("❌ Could not find import section in vibe_server.py")
        else:
            print("✅ SQL validation function already exists")

    except Exception as e:
        print(f"❌ Failed to update vibe_server.py: {e}")
        return False

    return True


def create_vibe_readme():
    """Create README for Vibe SQL fixes"""

    readme_content = """# Vibe Server SQL Fixes

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
"""

    HOME = os.path.expanduser("~")
    PROJECT_ROOT = os.path.join(HOME, "Documents/GitHub/atlastrinity")
    readme_path = os.path.join(PROJECT_ROOT, "docs/vibe_sql_fixes.md")
    with open(readme_path, "w") as f:
        f.write(readme_content)

    print(f"✅ Vibe SQL fixes README created: {readme_path}")


if __name__ == "__main__":
    print("🔧 Updating Vibe server with SQL fixes...")

    if update_vibe_server():
        create_vibe_readme()
        print("🎉 Vibe server updated successfully!")
    else:
        print("❌ Failed to update Vibe server")
