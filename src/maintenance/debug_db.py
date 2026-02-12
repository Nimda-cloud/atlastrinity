import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import desc, select

PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.brain.memory.db.manager import db_manager
from src.brain.memory.db.schema import TaskStep, ToolExecution

# Ensure CONFIG_ROOT is set correctly
os.environ["CONFIG_ROOT"] = os.path.expanduser("~/.config/atlastrinity")


async def inspect():
    await db_manager.initialize()
    async with await db_manager.get_session() as session:
        # Get latest 10 tool executions
        stmt = select(ToolExecution).order_by(desc(ToolExecution.created_at)).limit(10)
        results = await session.execute(stmt)
        executions = results.scalars().all()

        for ex in executions:
            pass

        # Get latest 5 Steps to compare IDs
        stmt = select(TaskStep).order_by(desc(TaskStep.created_at)).limit(5)
        results = await session.execute(stmt)
        steps = results.scalars().all()

        for s in steps:
            pass


if __name__ == "__main__":
    asyncio.run(inspect())
