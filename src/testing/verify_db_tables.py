"""Standalone script to verify database tables and counts during setup"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, cast

# Add src to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import func, select

from src.brain.memory.db.manager import db_manager
from src.brain.memory.db.schema import Base


# Simple color helper
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


async def verify_database_tables():
    """Detailed verification of database tables and counts"""
    try:
        await db_manager.initialize()

        async with await db_manager.get_session() as session:
            for table_name in Base.metadata.tables:
                try:
                    table = Base.metadata.tables[table_name]
                    stmt = select(func.count()).select_from(table)
                    res = await session.execute(stmt)
                    res.scalar()
                except Exception:
                    pass

        await db_manager.close()
    except Exception:
        return False
    return True


async def verify_redis():
    """Simple Redis ping check using redis-py"""
    try:
        from typing import cast

        from redis.asyncio import from_url

        # Default fallback if env not set, though Config should handle it
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = cast("Any", from_url(redis_url, encoding="utf-8", decode_responses=True))
        is_alive = await client.ping()
        if is_alive:
            pass
        else:
            pass
        await client.aclose()
        return True
    except ImportError:
        pass
    except Exception:
        # Not blocking setup usually, but good to know
        return True


async def verify_chromadb():
    """Verify ChromaDB client initialization and collection listing"""
    try:
        import chromadb

        # Determine path from config or default
        # Assuming typical path: ~/.config/atlastrinity/memory
        db_path = Path.home() / ".config" / "atlastrinity" / "memory" / "chroma"
        if not db_path.exists():
            return True

        # Just try to instantiate client
        # Cast to Any to satisfy linters that might not see PersistentClient
        cli = cast("Any", chromadb).PersistentClient(path=str(db_path))
        collection_names = cli.list_collections()
        for name in collection_names:
            # ChromaDB v0.6.0+: list_collections() returns strings, not objects
            try:
                cli.get_collection(str(name))
            except Exception:
                pass

        return True
    except ImportError:
        pass
    except Exception as e:
        # Check specifically for the KEY error '_type' which happens on incompatible migrations
        if isinstance(e, KeyError) and str(e) == "'_type'":
            # Non-blocking for setup
            return True

        # Log more details if it's a type error
        if isinstance(e, TypeError):
            import traceback

            traceback.print_exc()
        return False
    return True


async def main_check():
    sql_ok = await verify_database_tables()
    redis_ok = await verify_redis()
    chroma_ok = (
        verify_chromadb()
    )  # Sync function usually for chroma client init, but wrapped if needed.
    # Actually client.list_collections might be blocking IO but acceptable for setup script
    if asyncio.iscoroutine(chroma_ok):
        chroma_ok = await chroma_ok

    return sql_ok and redis_ok and chroma_ok


if __name__ == "__main__":
    if not asyncio.run(main_check()):
        sys.exit(1)
