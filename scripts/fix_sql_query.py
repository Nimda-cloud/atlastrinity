#!/usr/bin/env python3
"""
Fix SQL query for vibe_check_db
"""

import os
import sqlite3


def fix_vibe_check_query():
    """Fix the UNION ALL query in vibe_check_db"""

    db_path = os.path.expanduser("~/.config/atlastrinity/atlastrinity.db")

    # Test the corrected query
    corrected_query = """
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
    ORDER BY order_field DESC 
    LIMIT 50
    """

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Test the corrected query
        cursor.execute(corrected_query)
        results = cursor.fetchall()

        print(f"✅ Corrected query works! Found {len(results)} results")

        conn.close()
        return corrected_query

    except Exception as e:
        print(f"❌ Query failed: {e}")
        return None


if __name__ == "__main__":
    fix_vibe_check_query()
