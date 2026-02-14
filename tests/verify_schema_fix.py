import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from sqlalchemy import text

    from src.brain.memory.db.manager import db_manager
except ImportError as e:
    print(f"CRITICAL: Failed to import brain modules: {e}")
    sys.exit(1)


async def verify_schema():
    print("Initializing Database...")
    await db_manager.initialize()

    if not db_manager.available:
        print("DB Initialization Failed.")
        sys.exit(1)

    print("Verifying 'files' table existence...")

    try:
        async with await db_manager.get_session() as session:
            # 1. Check if we can query the table
            stmt = text("SELECT count(*) FROM files")
            await session.execute(stmt)
            print(" -> Table 'files' exists and is queryable.")

            # 2. Check the specific query from Vibe logs
            # [SQL: SELECT * FROM files WHERE path LIKE '%workspace%']
            stmt_vibe = text("SELECT * FROM files WHERE path LIKE '%workspace%'")
            await session.execute(stmt_vibe)
            print(" -> Vibe query executed successfully (no error).")

    except Exception as e:
        print(f"VERIFICATION FAILED: {e}")
        sys.exit(1)

    print("VERIFICATION SUCCESSFUL.")
    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(verify_schema())
