import asyncio
import os
import sqlite3
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


async def fix_schema():
    from pathlib import Path

    db_path = Path.home() / ".config" / "atlastrinity" / "atlastrinity.db"
    print(f"Connecting to database at {db_path}...")

    if not os.path.exists(db_path):
        print(f"❌ Database file not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("Checking columns in 'tool_executions'...")
        cursor.execute("PRAGMA table_info(tool_executions)")
        columns = [row[1] for row in cursor.fetchall()]

        if "status" not in columns:
            print("Adding 'status' column to 'tool_executions'...")
            cursor.execute(
                "ALTER TABLE tool_executions ADD COLUMN status VARCHAR(50) DEFAULT 'SUCCESS'"
            )
            print("✅ Added 'status' column.")
        else:
            print("Column 'status' already exists.")

        conn.commit()
        conn.close()
        print("✅ Database schema fix completed successfully.")
    except Exception as e:
        print(f"❌ Failed to fix database schema: {e}")


if __name__ == "__main__":
    asyncio.run(fix_schema())
