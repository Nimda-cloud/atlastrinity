# PostgreSQL Migration Plan - AtlasTrinity

## 📋 Overview

**Status:** 🔄 **PLANNED** (Not implemented yet)  
**Priority:** 🟡 **MEDIUM** (Future implementation)  
**Target:** When database grows >10MB or high concurrency needed  

---

## 🎯 Why Consider PostgreSQL?

### **Current State (SQLite)**
```yaml
Database: ~/.config/atlastrinity/atlastrinity.db
Size: 102 KB (Jan 2026)
Engine: SQLite + aiosqlite
Tables: 13 active tables
Access: vibe_check_db + DatabaseManager
Performance: Excellent for current load
```

### **Triggers for Migration**
```yaml
Database Size: >10 MB
Concurrent Users: >5 agents simultaneously
Query Complexity: Need for window functions/CTEs
Performance: SQLite bottlenecks detected
Production: High-load deployment required
```

---

## 📊 Migration Benefits

| Feature | SQLite (Current) | PostgreSQL (Future) | Impact |
|---------|------------------|-------------------|--------|
| **Concurrency** | Limited writes | Full MVCC | 🚀 Multi-agent scaling |
| **Query Power** | Basic SQL | Window functions, CTEs | 📈 Complex analytics |
| **JSON Support** | Basic | Native JSONB | 🔍 Advanced queries |
| **Performance** | Good for <10MB | Excellent for large datasets | ⚡ Production ready |
| **Self-Healing** | Read-only via vibe | Full DDL operations | 🛠️ Schema fixes |
| **Agent Access** | Internal API | Direct MCP access | 🔓 Better integration |

---

## 🛠️ Implementation Plan

### **Phase 1: Environment Setup**

```bash
# Install PostgreSQL 17
brew install postgresql@17
brew services start postgresql@17

# Create database and user
createdb atlastrinity_prod
psql postgres -c "CREATE USER atlas WITH PASSWORD 'secure_password';"
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE atlastrinity_prod TO atlas;"

# Install Python dependencies
pip install asyncpg psycopg2-binary
```

### **Phase 2: MCP Server Implementation**

**File:** `src/mcp_server/postgres_server.py`

```python
"""PostgreSQL MCP Server with full capabilities for AtlasTrinity"""
import asyncio
import asyncpg
import os
from mcp.server import FastMCP
from typing import Any, Dict, List

server = FastMCP("postgres-server")

# Connection pool configuration
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "atlas",
    "password": os.getenv("POSTGRES_PASSWORD"),
    "database": "atlastrinity_prod",
    "min_size": 2,
    "max_size": 10
}

async def get_pool():
    """Create or get connection pool"""
    return await asyncpg.create_pool(**POSTGRES_CONFIG)

@server.tool()
async def postgres_query(query: str) -> Dict[str, Any]:
    """Execute read-only SQL query with safety checks"""
    
    # Safety: Only allow SELECT queries
    if not query.strip().upper().startswith("SELECT"):
        return {"error": "Only SELECT queries allowed"}
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            result = await conn.fetch(query)
            return {
                "success": True,
                "rows": [dict(row) for row in result],
                "count": len(result)
            }
        except Exception as e:
            return {"error": str(e)}

@server.tool()
async def postgres_execute(query: str) -> Dict[str, Any]:
    """Execute write query (INSERT/UPDATE/DELETE) for self-healing"""
    
    # Safety: Allow only specific operations
    allowed_operations = ["INSERT", "UPDATE", "DELETE"]
    operation = query.strip().upper().split()[0]
    
    if operation not in allowed_operations:
        return {"error": f"Operation {operation} not allowed"}
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            result = await conn.execute(query)
            return {
                "success": True,
                "affected": result,
                "operation": operation
            }
        except Exception as e:
            return {"error": str(e)}

@server.tool()
async def postgres_schema_alter(ddl: str) -> Dict[str, Any]:
    """Execute DDL for self-healing schema fixes"""
    
    # Safety: Only allow specific DDL operations
    allowed_ddl = ["ALTER TABLE", "CREATE INDEX", "DROP INDEX", "ADD COLUMN"]
    ddl_upper = ddl.strip().upper()
    
    if not any(ddl_upper.startswith(op) for op in allowed_ddl):
        return {"error": "DDL operation not allowed"}
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(ddl)
            return {
                "success": True,
                "ddl": ddl.strip(),
                "message": "Schema updated successfully"
            }
        except Exception as e:
            return {"error": str(e)}

@server.tool()
async def postgres_list_tables(schema: str = "public") -> Dict[str, Any]:
    """List all tables in specified schema"""
    
    query = """
    SELECT table_name, table_type 
    FROM information_schema.tables 
    WHERE table_schema = $1
    ORDER BY table_name
    """
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            result = await conn.fetch(query, schema)
            return {
                "success": True,
                "tables": [dict(row) for row in result],
                "schema": schema
            }
        except Exception as e:
            return {"error": str(e)}

@server.tool()
async def postgres_describe_table(table_name: str, schema: str = "public") -> Dict[str, Any]:
    """Get detailed table schema information"""
    
    query = """
    SELECT 
        column_name,
        data_type,
        is_nullable,
        column_default,
        character_maximum_length
    FROM information_schema.columns 
    WHERE table_schema = $1 AND table_name = $2
    ORDER BY ordinal_position
    """
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            result = await conn.fetch(query, schema, table_name)
            return {
                "success": True,
                "table": table_name,
                "schema": schema,
                "columns": [dict(row) for row in result]
            }
        except Exception as e:
            return {"error": str(e)}

@server.tool()
async def postgres_health_check() -> Dict[str, Any]:
    """Check PostgreSQL connection and basic stats"""
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            # Test connection
            version = await conn.fetchval("SELECT version()")
            
            # Get table count
            table_count = await conn.fetchval(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
            )
            
            # Get database size
            db_size = await conn.fetchval(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            )
            
            return {
                "success": True,
                "version": version.split(",")[0],
                "table_count": table_count,
                "database_size": db_size,
                "status": "healthy"
            }
        except Exception as e:
            return {"error": str(e), "status": "unhealthy"}

if __name__ == "__main__":
    import asyncio
    asyncio.run(server.run())
```

### **Phase 3: Data Migration**

**File:** `scripts/migrate_sqlite_to_postgres.py`

```python
"""Migration script from SQLite to PostgreSQL"""
import asyncio
import sqlite3
import asyncpg
from pathlib import Path
from datetime import datetime

# Configuration
SQLITE_DB = Path.home() / ".config" / "atlastrinity" / "atlastrinity.db"
POSTGRES_URL = "postgresql://atlas:secure_password@localhost/atlastrinity_prod"

async def migrate_table(table_name: str, pg_conn: asyncpg.Connection, sqlite_conn: sqlite3.Connection):
    """Migrate a single table from SQLite to PostgreSQL"""
    
    # Get SQLite data
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    
    if not rows:
        print(f"  Table {table_name}: No data to migrate")
        return
    
    # Prepare PostgreSQL insert query
    placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
    insert_query = f'INSERT INTO {table_name} VALUES ({placeholders})'
    
    # Migrate data in batches
    batch_size = 100
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        
        try:
            await pg_conn.executemany(insert_query, batch)
            print(f"  Table {table_name}: Migrated {len(batch)} rows")
        except Exception as e:
            print(f"  Table {table_name}: Error - {e}")
            raise

async def main():
    """Main migration process"""
    
    print("🚀 Starting SQLite to PostgreSQL migration...")
    
    # Connect to PostgreSQL
    pg_conn = await asyncpg.connect(POSTGRES_URL)
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    
    try:
        # Tables to migrate (in order of dependencies)
        tables = [
            "sessions",
            "tasks", 
            "task_steps",
            "tool_executions",
            "logs",
            "kg_nodes",
            "kg_edges",
            "agent_messages",
            "recovery_attempts",
            "conversation_summaries",
            "behavioral_deviations",
            "knowledge_promotions"
        ]
        
        for table in tables:
            print(f"📦 Migrating {table}...")
            await migrate_table(table, pg_conn, sqlite_conn)
        
        print("✅ Migration completed successfully!")
        
        # Verify migration
        for table in tables:
            count = await pg_conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            print(f"  {table}: {count} rows")
            
    finally:
        await pg_conn.close()
        sqlite_conn.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### **Phase 4: Configuration Updates**

**Update:** `~/.config/atlastrinity/mcp/config.json`

```json
{
  "mcpServers": {
    "postgres": {
      "command": "python3",
      "args": ["-m", "src.mcp_server.postgres_server"],
      "disabled": false,
      "tier": 2,
      "category": "database",
      "description": "PostgreSQL Database Access with Full Capabilities",
      "agents": ["atlas", "tetyana", "grisha"],
      "capabilities": [
        "Execute read-only SQL queries",
        "Execute write queries (INSERT/UPDATE/DELETE)",
        "Schema modifications (ALTER TABLE, CREATE INDEX)",
        "Table introspection",
        "Health monitoring"
      ]
    }
  }
}
```

**Update:** `~/.config/atlastrinity/config.yaml`

```yaml
database:
  # Switch from SQLite to PostgreSQL
  url: "postgresql+asyncpg://atlas:${POSTGRES_PASSWORD}@localhost/atlastrinity_prod"
  # Old: sqlite+aiosqlite:///${CONFIG_ROOT}/atlastrinity.db
  
  pool_size: 20
  max_overflow: 10
  pool_pre_ping: true
```

---

## 🔄 Self-Healing Integration

### **Enhanced Capabilities with PostgreSQL**

```python
# Enhanced self-healing with PostgreSQL
class PostgreSQLSelfHealing:
    """Self-healing with full database capabilities"""
    
    async def fix_missing_column(self, table: str, column: str, column_type: str):
        """Add missing column for schema consistency"""
        
        ddl = f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"
        
        result = await manager.call_tool("postgres", "postgres_schema_alter", {
            "ddl": ddl
        })
        
        return result
    
    async def create_performance_index(self, table: str, columns: List[str]):
        """Create index for performance optimization"""
        
        index_name = f"idx_{table}_{'_'.join(columns)}"
        ddl = f"CREATE INDEX {index_name} ON {table} ({', '.join(columns)})"
        
        result = await manager.call_tool("postgres", "postgres_schema_alter", {
            "ddl": ddl
        })
        
        return result
    
    async def analyze_query_performance(self, query: str):
        """Analyze slow queries and suggest optimizations"""
        
        explain_query = f"EXPLAIN ANALYZE {query}"
        
        result = await manager.call_tool("postgres", "postgres_query", {
            "query": explain_query
        })
        
        return result
```

### **Self-Healing Workflow with PostgreSQL**

```mermaid
flowchart TD
    Error[Error Detected] --> Analyze[Analyze Error Type]
    
    Analyze --> |Schema Issue| SchemaFix[PostgreSQL Schema Fix]
    Analyze --> |Data Issue| DataFix[PostgreSQL Data Fix]
    Analyze --> |Performance Issue| PerfFix[PostgreSQL Index Fix]
    
    SchemaFix --> Verify[Verify Fix]
    DataFix --> Verify
    PerfFix --> Verify
    
    Verify --> Test[Run Tests]
    Test --> |Pass| Complete[Self-Healing Complete]
    Test --> |Fail| SchemaFix
    
    style SchemaFix fill:#e1f5ff
    style DataFix fill:#e1ffe1
    style PerfFix fill:#fff5e1
```

---

## 📈 Performance Comparison

### **Benchmarks (Expected)**

| Operation | SQLite (102KB) | PostgreSQL (Target) | Improvement |
|-----------|----------------|-------------------|-------------|
| **Simple SELECT** | 1ms | 0.5ms | 2x faster |
| **Complex JOIN** | 50ms | 10ms | 5x faster |
| **Concurrent Writes** | Queue | Parallel | 10x throughput |
| **JSON Queries** | Parse time | Native | 20x faster |
| **Window Functions** | Not supported | 5ms | New capability |

---

## 🔒 Security Considerations

### **PostgreSQL Security Setup**

```sql
-- Create dedicated user for AtlasTrinity
CREATE USER atlas WITH PASSWORD 'secure_password';

-- Grant limited permissions (not superuser)
GRANT CONNECT ON DATABASE atlastrinity_prod TO atlas;
GRANT USAGE ON SCHEMA public TO atlas;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO atlas;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO atlas;

-- Row Level Security (optional)
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY session_policy ON sessions FOR ALL USING (session_id = current_setting('app.current_session_id'));
```

### **MCP Server Security**

```python
# Safety checks in postgres_server.py
SAFE_OPERATIONS = {
    "SELECT": ["SELECT", "WITH"],
    "WRITE": ["INSERT", "UPDATE", "DELETE"],
    "DDL": ["ALTER TABLE", "CREATE INDEX", "DROP INDEX", "ADD COLUMN"]
}

def validate_query(query: str, operation_type: str) -> bool:
    """Validate query safety"""
    
    allowed_prefixes = SAFE_OPERATIONS.get(operation_type, [])
    query_upper = query.strip().upper()
    
    return any(query_upper.startswith(prefix) for prefix in allowed_prefixes)
```

---

## 📅 Implementation Timeline

### **Phase 1: Preparation (Week 1)**
- [ ] Install PostgreSQL 17
- [ ] Setup database and user
- [ ] Install Python dependencies
- [ ] Create backup strategy

### **Phase 2: Development (Week 2)**
- [ ] Implement `postgres_server.py`
- [ ] Create migration script
- [ ] Add comprehensive tests
- [ ] Update documentation

### **Phase 3: Migration (Week 3)**
- [ ] Backup SQLite database
- [ ] Run migration script
- [ ] Verify data integrity
- [ ] Update configuration

### **Phase 4: Testing (Week 4)**
- [ ] Test all MCP tools
- [ ] Verify self-healing workflows
- [ ] Performance benchmarking
- [ ] Security audit

### **Phase 5: Deployment (Week 5)**
- [ ] Switch production to PostgreSQL
- [ ] Monitor performance
- [ ] Fine-tune configuration
- [ ] Archive SQLite backup

---

## 🎯 Success Criteria

### **Technical Metrics**
- [ ] All 13 tables migrated successfully
- [ ] Zero data loss during migration
- [ ] MCP health check passes
- [ ] Self-healing workflows functional
- [ ] Performance improvement >2x for complex queries

### **Operational Metrics**
- [ ] All agents can access PostgreSQL
- [ ] Zero downtime during migration
- [ ] Backup and recovery procedures tested
- [ ] Documentation complete and up-to-date

---

## 📝 Notes for Future Implementation

### **Key Decisions Made**
1. **Keep SQLite for now** - Current size (102KB) doesn't justify complexity
2. **Use asyncpg** - Best async PostgreSQL driver for Python
3. **Custom MCP server** - Better control than deprecated NPM package
4. **Schema ready** - Current SQLAlchemy schema already supports PostgreSQL
5. **Migration script** - Automated data transfer with verification

### **Future Enhancements**
- **Read replicas** for high availability
- **Connection pooling** optimization
- **Query caching** layer
- **Real-time analytics** with PostgreSQL extensions
- **Geospatial queries** if needed

---

## 📞 Implementation Contact

When ready to implement:
1. Review this document
2. Check current database size and performance
3. Run `python scripts/check_database_size.py`
4. Contact Atlas team for migration planning

**Document Version:** 1.0.0  
**Created:** 2026-01-26  
**Status:** 🔄 **PLANNED**  
**Next Review:** When database >5MB or performance issues detected
