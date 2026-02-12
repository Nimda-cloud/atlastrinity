import asyncio
import sys
from pathlib import Path

from sqlalchemy import func, select

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.brain.config.config_loader import config
from src.brain.memory.db.manager import db_manager

# Use dynamic DB_URL
DB_URL = config.get("db.url", "sqlite+aiosqlite:///:memory:")
from src.brain.memory.db.schema import (
    ConversationSummary,
    KGNode,
    Session,
    Task,
    TaskStep,
    ToolExecution,
)
from src.brain.memory.memory import long_term_memory


async def verify_storage():

    # 1. Verify PostgreSQL
    try:
        await db_manager.initialize()
        if not db_manager.available:
            pass
        else:
            async with await db_manager.get_session() as session:

                async def count(model):
                    res = await session.execute(select(func.count(model.id)))
                    return res.scalar()

                session_count = await count(Session)
                await count(Task)
                await count(TaskStep)
                await count(ToolExecution)
                await count(KGNode)
                await count(ConversationSummary)

                if session_count is not None and session_count > 0:
                    pass
                else:
                    pass

    except Exception:
        pass

    # 2. Verify ChromaDB
    try:
        stats = long_term_memory.get_stats()
        if not stats.get("available"):
            pass
        else:
            # Check Knowledge Graph Nodes in Chroma
            long_term_memory.knowledge.count()

            # Check Conversations in Chroma
            long_term_memory.conversations.count()

            # Try simple query to ensure embeddings work
            try:
                long_term_memory.recall_similar_tasks("test task", n_results=1)
            except Exception:
                pass

    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(verify_storage())
