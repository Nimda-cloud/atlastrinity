import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import desc, select

PROJECT_ROOT = str(Path(__file__).parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.brain.db.manager import db_manager
from src.brain.db.schema import TaskStep, ToolExecution

# Ensure CONFIG_ROOT is set correctly
os.environ["CONFIG_ROOT"] = os.path.expanduser("~/.config/atlastrinity")


async def inspect():
    await db_manager.initialize()
    async with await db_manager.get_session() as session:
        # Get latest 10 tool executions
        stmt = select(ToolExecution).order_by(desc(ToolExecution.created_at)).limit(10)
        results = await session.execute(stmt)
        executions = results.scalars().all()

        print("--- Latest Tool Executions ---")
        for ex in executions:
            print(f"ID: {ex.id}")
            print(f"Step ID (FK): {ex.step_id}")
            print(f"Tool: {ex.server_name}.{ex.tool_name}")
            print(f"Result Prefix: {str(ex.result)[:50]}...")
            print(f"Created: {ex.created_at}")
            print("-" * 20)

        # Get latest 5 Steps to compare IDs
        stmt = select(TaskStep).order_by(desc(TaskStep.created_at)).limit(5)
        results = await session.execute(stmt)
        steps = results.scalars().all()

        print("\n--- Latest Task Steps ---")
        for s in steps:
            print(f"Step UUID: {s.id}")
            print(f"Sequence Num: {s.sequence_number}")
            print(f"Action: {s.action[:50]}...")
            print("-" * 20)


if __name__ == "__main__":
    asyncio.run(inspect())
