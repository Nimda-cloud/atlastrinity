"""
Patch for vibe_check_db SQL query issues
"""

import os
import sqlite3


def create_vibe_check_db_patch():
    """Create a patch file for vibe_check_db"""

    patch_content = """
# Patch for vibe_check_db SQL UNION ALL ORDER BY issue

## Problem
The original query fails because UNION ALL requires all SELECT statements to have the same number and type of columns, and ORDER BY must reference columns that exist in the final result set.

## Original (Broken) Query
```sql
SELECT 
    'tool_executions' as source_table, 
    te.tool_name, te.arguments, te.result, te.created_at, 
    ts.action, ts.sequence_number
FROM tool_executions te 
JOIN task_steps ts ON te.step_id = ts.id 
WHERE te.result LIKE '%Служанка%' 
   OR te.arguments LIKE '%Служанка%' 

UNION ALL 

SELECT 
    'task_steps' as source_table, 
    NULL, NULL, NULL, NULL, 
    ts.action, ts.sequence_number
FROM task_steps ts 
WHERE ts.action LIKE '%Служанка%' 

UNION ALL 

SELECT 
    'logs' as source_table, 
    NULL, NULL, NULL, NULL, 
    l.message, NULL
FROM logs l 
WHERE l.message LIKE '%Служанка%' 

ORDER BY 
    CASE 
        WHEN source_table = 'tool_executions' THEN created_at
        WHEN source_table = 'logs' THEN timestamp
        ELSE NULL
    END DESC 
LIMIT 50
```

## Fixed Query
```sql
SELECT * FROM (
    SELECT 
        'tool_executions' as source_table, 
        te.tool_name, te.arguments, te.result, te.created_at as created_at, 
        ts.action, ts.sequence_number, te.created_at as order_field
    FROM tool_executions te 
    JOIN task_steps ts ON te.step_id = ts.id 
    WHERE te.result LIKE '%Служанка%' 
       OR te.arguments LIKE '%Служанка%' 
    
    UNION ALL 
    
    SELECT 
        'task_steps' as source_table, 
        NULL as tool_name, NULL as arguments, NULL as result, NULL as created_at, 
        ts.action, ts.sequence_number, NULL as order_field
    FROM task_steps ts 
    WHERE ts.action LIKE '%Служанка%' 
    
    UNION ALL 
    
    SELECT 
        'logs' as source_table, 
        NULL as tool_name, NULL as arguments, NULL as result, l.timestamp as created_at, 
        l.message as action, NULL as sequence_number, l.timestamp as order_field
    FROM logs l 
    WHERE l.message LIKE '%Служанка%'
)
ORDER BY order_field DESC NULLS LAST
LIMIT 50
```

## Key Changes
1. Added explicit column aliases with NULL placeholders
2. Created a unified `order_field` column for sorting
3. Used `NULLS LAST` to handle NULL values properly
4. Wrapped in subquery to allow ORDER BY on computed column
"""

    # Write patch to file
    HOME = os.path.expanduser("~")
    PROJECT_ROOT = os.path.join(HOME, "Documents/GitHub/atlastrinity")
    patch_file = os.path.join(PROJECT_ROOT, "docs/sql_patch.md")
    with open(patch_file, "w") as f:
        f.write(patch_content)

    print(f"✅ SQL patch created: {patch_file}")
    return patch_file


def test_fixed_query():
    """Test the fixed SQL query"""

    db_path = os.path.expanduser("~/.config/atlastrinity/atlastrinity.db")

    fixed_query = """
    SELECT * FROM (
        SELECT 
            'tool_executions' as source_table, 
            te.tool_name, te.arguments, te.result, te.created_at as created_at, 
            ts.action, ts.sequence_number, te.created_at as order_field
        FROM tool_executions te 
        JOIN task_steps ts ON te.step_id = ts.id 
        WHERE te.result LIKE '%Служанка%' 
           OR te.arguments LIKE '%Служанка%' 
        
        UNION ALL 
        
        SELECT 
            'task_steps' as source_table, 
            NULL as tool_name, NULL as arguments, NULL as result, NULL as created_at, 
            ts.action, ts.sequence_number, NULL as order_field
        FROM task_steps ts 
        WHERE ts.action LIKE '%Служанка%' 
        
        UNION ALL 
        
        SELECT 
            'logs' as source_table, 
            NULL as tool_name, NULL as arguments, NULL as result, l.timestamp as created_at, 
            l.message as action, NULL as sequence_number, l.timestamp as order_field
        FROM logs l 
        WHERE l.message LIKE '%Служанка%'
    )
    ORDER BY order_field DESC NULLS LAST
    LIMIT 50
    """

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(fixed_query)
        results = cursor.fetchall()

        print(f"✅ Fixed query works! Found {len(results)} results")

        # Show sample results
        if results:
            print("\nSample results:")
            for i, row in enumerate(results[:3]):
                print(f"  {i + 1}. {row[0]} - {row[4]}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Fixed query failed: {e}")
        return False


if __name__ == "__main__":
    create_vibe_check_db_patch()
    test_fixed_query()
