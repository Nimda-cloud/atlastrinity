
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
