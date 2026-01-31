#!/usr/bin/env python3
"""
Fixed Atlas Trinity Memory Cleanup Script

This script properly clears cached data, memory, and temporary files.
"""

import asyncio
import sys
import shutil
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from src.brain.db.manager import db_manager
from src.brain.memory import long_term_memory


def clear_cache():
    """Clear all cache directories"""
    print("🧹 Clearing cache directories...")
    
    cache_dirs = [
        project_root / "__pycache__",
        project_root / "src" / "__pycache__",
        project_root / ".venv" / "__pycache__",
        Path("/Users/dev/.config/atlastrinity/cache"),
        project_root / "node_modules" / ".cache",
        project_root / ".vite",
    ]
    
    cleared_count = 0
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            try:
                if cache_dir.is_file():
                    cache_dir.unlink()
                    print(f"✅ Deleted cache file: {cache_dir}")
                else:
                    shutil.rmtree(cache_dir)
                    print(f"✅ Deleted cache directory: {cache_dir}")
                cleared_count += 1
            except Exception as e:
                print(f"⚠️ Could not delete {cache_dir}: {e}")
        else:
            print(f"ℹ️ Cache directory not found: {cache_dir}")
    
    print(f"✅ Cleared {cleared_count} cache directories.")


def clear_chroma_files():
    """Force clear ChromaDB files"""
    print("🧹 Force clearing ChromaDB files...")
    
    chroma_paths = [
        Path("/Users/dev/.config/atlastrinity/memory/chroma"),
        Path("/Users/dev/.config/atlastrinity/data/golden_fund/chroma_db"),
    ]
    
    for chroma_path in chroma_paths:
        if chroma_path.exists():
            try:
                shutil.rmtree(chroma_path)
                print(f"✅ Deleted ChromaDB directory: {chroma_path}")
            except Exception as e:
                print(f"⚠️ Could not delete {chroma_path}: {e}")
        else:
            print(f"ℹ️ ChromaDB directory not found: {chroma_path}")
    
    # Also delete any SQLite files
    sqlite_files = list(Path("/Users/dev/.config/atlastrinity").rglob("*.sqlite3"))
    for sqlite_file in sqlite_files:
        try:
            sqlite_file.unlink()
            print(f"✅ Deleted SQLite file: {sqlite_file}")
        except Exception as e:
            print(f"⚠️ Could not delete {sqlite_file}: {e}")


async def clear_experience():
    print("🧹 Clearing all AtlasTrinity experience...")

    # 0. Clear cache first
    clear_cache()
    clear_chroma_files()

    # 1. Clear Database (SQLite/PostgreSQL)
    if not db_manager.available:
        await db_manager.initialize()

    if db_manager.available and db_manager._engine:
        try:
            async with db_manager._engine.begin() as conn:
                print("Deleting from database tables...")
                # Disable foreign key constraints for SQLite
                await conn.execute(text("PRAGMA foreign_keys = OFF"))
                
                # Order matters due to FKs - delete in reverse order of creation
                tables = [
                    "kg_edges",
                    "kg_nodes", 
                    "logs",           # Delete logs first (no FK dependencies)
                    "tool_executions", # Depends on task_steps
                    "task_steps",     # Depends on tasks
                    "tasks",          # Depends on sessions
                    "sessions",       # Root table
                ]
                for table in tables:
                    # Use DELETE FROM instead of TRUNCATE for SQLite compatibility
                    await conn.execute(text(f"DELETE FROM {table}"))
                    print(f"✅ Cleared table {table}")
                
                # Re-enable foreign key constraints
                await conn.execute(text("PRAGMA foreign_keys = ON"))
                print("✅ Database tables cleared.")
        except Exception as e:
            print(f"❌ Failed to clear database: {e}")

    # 2. Clear ChromaDB completely
    if long_term_memory.available:
        try:
            print("Deleting ChromaDB collections...")
            # Delete all collections
            for collection_name in ["lessons", "strategies", "knowledge_graph_nodes"]:
                try:
                    long_term_memory.client.delete_collection(collection_name)
                    print(f"✅ Deleted collection {collection_name}")
                except Exception:
                    print(f"ℹ️ Collection {collection_name} does not exist or already deleted.")

            # Reset the memory attributes to force re-creation
            long_term_memory.lessons = None
            long_term_memory.strategies = None
            long_term_memory.knowledge = None
            
            print("✅ ChromaDB collections completely cleared.")
        except Exception as e:
            print(f"❌ Failed to clear ChromaDB: {e}")
    else:
        print("ℹ️ ChromaDB not available, skipping.")

    print("\n✨ All experience and cache has been reset. Atlas is now a blank slate.")


if __name__ == "__main__":
    asyncio.run(clear_experience())
