import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = str(Path(__file__).parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text

from src.brain.db.manager import db_manager


async def check():
    await db_manager.initialize()
    async with await db_manager.get_session() as session:
        result = await session.execute(
            text("""
            SELECT te.tool_name, te.arguments, te.result, ts.sequence_number 
            FROM tool_executions te
            JOIN task_steps ts ON te.step_id = ts.id
            WHERE ts.sequence_number = '3'
            ORDER BY te.created_at DESC LIMIT 5;
        """)
        )
        print("\n--- Tool Executions for Step 3 ---")
        for row in result:
            print(f"Step {row.sequence_number} | Tool: {row.tool_name}")
            print(f"Args: {row.arguments}")
            print(f"Result: {row.result}")
            print("-" * 40)


if __name__ == "__main__":
    asyncio.run(check())
