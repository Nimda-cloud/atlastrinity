
import asyncio
import os
import sys
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to path
sys.path.append(os.getcwd())

from src.brain.db.manager import DB_URL
from src.brain.db.schema import Base

async def verify_tables():
    print(f"Connecting to database: {DB_URL}")
    engine = create_async_engine(DB_URL)
    
    try:
        async with engine.connect() as conn:
            def get_db_info(connection):
                inspector = inspect(connection)
                tables = inspector.get_table_names()
                info = {}
                for table in tables:
                    columns = inspector.get_columns(table)
                    info[table] = [c['name'] for c in columns]
                return info
            
            db_info = await conn.run_sync(get_db_info)
            actual_tables = list(db_info.keys())
            
            expected_tables = Base.metadata.tables
            
            print("\nTable & Column Verification Result:")
            print("-" * 40)
            
            all_ok = True
            for table_name, table_obj in expected_tables.items():
                if table_name in actual_tables:
                    actual_cols = db_info[table_name]
                    expected_cols = [c.name for c in table_obj.columns]
                    
                    missing_cols = [c for c in expected_cols if c not in actual_cols]
                    
                    if not missing_cols:
                        print(f"✅ {table_name}: EXISTS (Columns: {len(actual_cols)}/{len(expected_cols)})")
                    else:
                        print(f"❌ {table_name}: MISSING COLUMNS: {missing_cols}")
                        all_ok = False
                else:
                    print(f"❌ {table_name}: MISSING TABLE")
                    all_ok = False
            
            if all_ok:
                print("\nSUCCESS: All schema tables and columns are present in the database.")
            else:
                print("\nFAILURE: Schema mismatch detected.")
                
    except Exception as e:
        print(f"\nERROR: Failed to connect or verify: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_tables())
