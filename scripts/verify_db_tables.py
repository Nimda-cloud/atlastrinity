"""Standalone script to verify database tables and counts during setup"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, cast

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, select

from src.brain.db.manager import db_manager
from src.brain.db.schema import Base


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
    print("\n[DB CHECK] Verifying SQL Tables...")
    try:
        await db_manager.initialize()

        async with await db_manager.get_session() as session:
            print(f"[DB] Found {len(Base.metadata.tables)} tables in schema.")
            for table_name in Base.metadata.tables:
                try:
                    table = Base.metadata.tables[table_name]
                    stmt = select(func.count()).select_from(table)
                    res = await session.execute(stmt)
                    count = res.scalar()
                    print(f"[DB]   - Table '{table_name}': {count} records")
                except Exception as e:
                    print(f"[DB] WARNING: Could not verify table '{table_name}': {e}")

        await db_manager.close()
    except Exception as e:
        print(f"[DB] ERROR during table verification: {e}")
        return False
    return True


async def verify_redis():
    """Simple Redis ping check using redis-py"""
    print("\n[DB CHECK] Verifying Redis...")
    try:
        from typing import cast

        from redis.asyncio import from_url

        # Default fallback if env not set, though Config should handle it
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = cast("Any", from_url(redis_url, encoding="utf-8", decode_responses=True))
        is_alive = await client.ping()
        if is_alive:
            print("[DB]   - Redis PING: PONG (Connection Successful)")
        else:
            print("[DB]   - Redis PING Failed")
        await client.aclose()
        return True
    except ImportError:
        print("[DB] WARNING: redis-py not installed. Skipping check.")
    except Exception as e:
        print(f"[DB] Redis Error: {e}")
        # Not blocking setup usually, but good to know
        return True


async def verify_chromadb():
    """Verify ChromaDB client initialization and collection listing"""
    print("\n[DB CHECK] Verifying ChromaDB (Vector Store)...")
    try:
        import chromadb

        # Determine path from config or default
        # Assuming typical path: ~/.config/atlastrinity/memory
        db_path = Path.home() / ".config" / "atlastrinity" / "memory" / "chroma"
        if not db_path.exists():
            print(
                f"[DB]   - ChromaDB path {db_path} does not exist yet (Normal for fresh install)."
            )
            return True

        # Just try to instantiate client
        # Cast to Any to satisfy linters that might not see PersistentClient
        cli = cast("Any", chromadb).PersistentClient(path=str(db_path))
        collection_names = cli.list_collections()
        print("[DB]   - ChromaDB Client Initialized")
        print(f"[DB]   - Collections found: {len(collection_names)}")
        for name in collection_names:
            # ChromaDB v0.6.0+: list_collections() returns strings, not objects
            try:
                col = cli.get_collection(str(name))
                print(f"[DB]     * {name} (count: {col.count()})")
            except Exception:
                print(f"[DB]     * {name} (count: ?)")

        return True
    except ImportError:
        print("[DB] WARNING: chromadb not installed. Skipping check.")
    except Exception as e:
        # Check specifically for the KEY error '_type' which happens on incompatible migrations
        if isinstance(e, KeyError) and str(e) == "'_type'":
            print(
                f"{Colors.FAIL}[DB] ChromaDB Error: Incompatible database format encountered (KeyError: '_type'){Colors.ENDC}"
            )
            print(
                f"{Colors.WARNING}[DB] This usually happens when an old backup is restored to a newer ChromaDB version (0.6.3+).{Colors.ENDC}"
            )
            print(
                f"{Colors.OKCYAN}[DB] FIX: Run 'rm -rf ~/.config/atlastrinity/memory/chroma' to reset the vector store.{Colors.ENDC}"
            )
            # Non-blocking for setup
            return True

        print(f"[DB] ChromaDB Error: {e}")
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
