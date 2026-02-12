import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import func, select

from src.brain.memory.db.manager import db_manager
from src.brain.memory.db.schema import AgentMessage, Session, Task, TaskStep, ToolExecution
from src.brain.memory.memory import long_term_memory


async def diagnose_db():
    if not db_manager.available:
        await db_manager.initialize()

    if not db_manager.available:
        return

    async with await db_manager.get_session() as session:
        # Count sessions
        await session.scalar(select(func.count(Session.id)))

        # Count tasks
        await session.scalar(select(func.count(Task.id)))

        # Count steps
        await session.scalar(select(func.count(TaskStep.id)))

        # Count tool executions
        await session.scalar(select(func.count(ToolExecution.id)))

        # Check for recursion (steps with dots)
        result = await session.execute(
            select(TaskStep.sequence_number).filter(TaskStep.sequence_number.contains(".")),
        )
        recursive_steps = result.scalars().all()
        if recursive_steps:
            pass

        # Check Inter-Agent Messaging
        await session.scalar(select(func.count(AgentMessage.id)))


async def diagnose_memory():
    stats = long_term_memory.get_stats()
    if stats.get("available"):
        pass
    else:
        pass


async def diagnose_browser():
    # Check if puppeteer is in MCP config and reachable
    from src.brain.mcp.mcp_manager import mcp_manager

    catalog = await mcp_manager.get_mcp_catalog()

    # Check if puppeteer is in catalog
    if "puppeteer" in catalog:
        pass
    else:
        pass

    if "macos-use" in catalog:
        pass


async def main():
    await diagnose_db()
    await diagnose_memory()
    await diagnose_browser()
    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
