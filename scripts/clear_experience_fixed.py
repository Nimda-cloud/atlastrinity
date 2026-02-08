"""
Fixed Atlas Trinity Memory Cleanup Script

This script properly clears cached data, memory, and temporary files.
"""

import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from src.brain.config import CONFIG_ROOT
from src.brain.db.manager import db_manager
from src.brain.memory import long_term_memory


def kill_processes():
    """Kill all project-related processes to free file locks"""
    print("🔪 Killing active project processes...")

    # Process patterns and names to kill
    process_patterns = [
        "vibe_server",
        "memory_server",
        "graph_server",
        "mcp-server",
        "macos-use",
        "brain.server",
    ]

    for pattern in process_patterns:
        try:
            # We use pkill for name matching
            subprocess.run(["pkill", "-9", "-f", pattern], check=False, capture_output=True)
        except Exception:
            pass

    # Port specific (8000, 8088 - skip UI ports 3000/5173 to avoid browser/IDE hangs)
    ports = [8000, 8088]
    for port in ports:
        try:
            # lsof -ti:PORT | xargs kill -9
            res = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
            if res.stdout.strip():
                pids = res.stdout.strip().split("\n")
                for pid in pids:
                    subprocess.run(["kill", "-9", pid], check=False)
        except Exception:
            pass

    print("✅ Processes terminated.")


def clear_redis():
    """Clear Redis data"""
    print("🧹 Clearing Redis cache...")
    try:
        # Check if redis-cli is available and flushall
        subprocess.run(["redis-cli", "flushall"], check=False, capture_output=True)
        print("✅ Redis flushed.")
    except Exception as e:
        print(f"⚠️ Could not flush Redis: {e}")


def clear_cache():
    """Clear all cache directories including recursive __pycache__"""
    print("🧹 Clearing cache directories...")

    # 1. Standard locations
    cache_dirs = [
        CONFIG_ROOT / "cache",
        project_root / "node_modules" / ".cache",
        project_root / ".vite",
        Path.home() / "Library" / "Caches" / "atlastrinity",
    ]

    # 2. Add recursive __pycache__ and logs
    print("🔍 Searching for recursive __pycache__ and logs...")

    # Logs
    log_dir = project_root / "logs"
    if log_dir.exists():
        for log_file in log_dir.glob("*"):
            try:
                if log_file.is_file():
                    log_file.unlink()
                elif log_file.is_dir():
                    shutil.rmtree(log_file)
            except Exception:
                pass
        print(f"✅ Cleared logs in {log_dir}")

    # Recursive __pycache__
    pycache_count = 0
    for root, dirs, _ in os.walk(project_root):
        depth = root[len(str(project_root)) :].count(os.sep)
        if depth > 5:
            continue
        for dir_name in dirs:
            if dir_name == "__pycache__":
                try:
                    shutil.rmtree(Path(root) / dir_name)
                    pycache_count += 1
                except Exception:
                    pass

    # Recursive .pyc
    for root, _, files in os.walk(project_root):
        depth = root[len(str(project_root)) :].count(os.sep)
        if depth > 5:
            continue
        for file_name in files:
            if file_name.endswith(".pyc"):
                try:
                    Path(root, file_name).unlink()
                except Exception:
                    pass

    cleared_count = 0
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            try:
                if cache_dir.is_file():
                    cache_dir.unlink()
                else:
                    shutil.rmtree(cache_dir)
                cleared_count += 1
                print(f"✅ Deleted: {cache_dir}")
            except Exception as e:
                print(f"⚠️ Could not delete {cache_dir}: {e}")

    print(f"✅ Cleared {cleared_count} standard cache paths and {pycache_count} __pycache__ dirs.")


def clear_chroma_files():
    """Force clear ChromaDB files"""
    print("🧹 Force clearing ChromaDB files...")

    chroma_paths = [
        CONFIG_ROOT / "memory" / "chroma",
        # project_root / "data" / "golden_fund" / "chroma_db", # Excluded: managed by clean:golden
    ]

    for chroma_path in chroma_paths:
        if chroma_path.exists():
            try:
                shutil.rmtree(chroma_path)
                print(f"✅ Deleted ChromaDB directory: {chroma_path}")
            except Exception as e:
                print(f"⚠️ Could not delete {chroma_path}: {e}")

    # Also delete any SQLite files in config root
    for root, _, files in os.walk(CONFIG_ROOT):
        depth = root[len(str(CONFIG_ROOT)) :].count(os.sep)
        if depth > 5:
            continue
        for file_name in files:
            if file_name.endswith(".sqlite3"):
                try:
                    Path(root, file_name).unlink()
                    print(f"✅ Deleted SQLite file: {Path(root, file_name)}")
                except Exception:
                    pass


async def cleanup_hallucinations():
    """Cleanup specific hallucinations as done in cleanup_memory.py"""
    if not long_term_memory.available:
        return

    print("🔍 Cleaning up specific hallucinations...")
    hallucinations = [
        "Сподівайся, як обходить",
        "я не маю прямого доступу до актуальних метеорологічних даних",
        "я не можу надати точний прогноз погоди",
        "нажаль я не маю доступу",
        "не маю доступу до інтернет",
        "я не маю прямого доступу до інтернету",
    ]

    for h in hallucinations:
        await long_term_memory.delete_specific_memory("conversations", h)
        await long_term_memory.delete_specific_memory("lessons", h)
    print("✅ Hallucination patterns cleared.")


async def clear_experience():
    print("╔══════════════════════════════════════════╗")
    print("║  AtlasTrinity Deep Cleanup & Reset       ║")
    print("╚══════════════════════════════════════════╝\n")

    # 1. Kill processes first to free locks
    kill_processes()

    # 2. Clear Redis
    clear_redis()

    # 3. Clear Database (SQLite/PostgreSQL)
    if not db_manager.available:
        try:
            await db_manager.initialize()
        except Exception:
            pass

    if db_manager.available and db_manager._engine:
        try:
            async with db_manager._engine.begin() as conn:
                print("🧹 Deleting from database tables...")
                # Disable foreign key constraints for SQLite
                await conn.execute(text("PRAGMA foreign_keys = OFF"))

                # Order matters due to FKs
                tables = [
                    "kg_edges",
                    "kg_nodes",
                    "logs",
                    "tool_executions",
                    "task_steps",
                    "tasks",
                    "sessions",
                ]
                for table in tables:
                    try:
                        await conn.execute(text(f"DELETE FROM {table}"))
                        print(f"✅ Cleared table {table}")
                    except Exception as e:
                        print(f"ℹ️ Table {table} skipped: {e}")

                # Re-enable foreign key constraints
                await conn.execute(text("PRAGMA foreign_keys = ON"))
                print("✅ Database tables cleared.")
        except Exception as e:
            print(f"❌ Failed to clear database: {e}")

    # 4. Clear ChromaDB collections via client
    if long_term_memory.available:
        try:
            print("🧠 Wiping all vector memory collections...")
            # Use the built-in method for a safe and complete reset
            await long_term_memory.clear_all_memory()

            # Special cleanup for hallucinations
            await cleanup_hallucinations()

            print("✅ ChromaDB collections completely cleared.")
        except Exception as e:
            print(f"❌ Failed to clear ChromaDB via client: {e}")
    else:
        print("ℹ️ ChromaDB not available, skipping client cleanup.")

    # 5. Clear file-system cache and logs LAST
    clear_cache()
    clear_chroma_files()

    print("\n✨ All experience, records, Redis and cache have been successfully reset.")
    print("🚀 Atlas is now a blank slate.")


if __name__ == "__main__":
    asyncio.run(clear_experience())
