import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text

from src.brain.memory.db.manager import db_manager


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
        """),
        )
        for _ in result:
            pass


if __name__ == "__main__":
    asyncio.run(check())
