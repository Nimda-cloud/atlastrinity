import asyncio
import os
import shutil
import sqlite3
import sys
from pathlib import Path

# Setup mock environment
MOCK_HOME = Path("/tmp/mock_atlastrinity_home")
if MOCK_HOME.exists():
    shutil.rmtree(MOCK_HOME)
MOCK_HOME.mkdir(parents=True)

MOCK_CONFIG = MOCK_HOME / ".config" / "atlastrinity"
MOCK_CONFIG.mkdir(parents=True)

# Setup paths
PROJECT_ROOT = Path("/Users/dev/Documents/GitHub/atlastrinity")
sys.path.insert(0, str(PROJECT_ROOT))

# We need to mock CONFIG_ROOT in memory to avoid polluting real ~/.config
import src.brain.config

src.brain.config.CONFIG_ROOT = MOCK_CONFIG


async def test_restoration_logic():
    print("--- Simulating New Machine Setup ---")

    # 1. Create a "Legacy" backup in the project root
    backup_dir = PROJECT_ROOT / "backups" / "databases"
    backup_dir.mkdir(parents=True, exist_ok=True)

    legacy_db_path = backup_dir / "atlastrinity.db"

    # Remove existing legacy backup to start clean
    if legacy_db_path.exists():
        legacy_db_path.unlink()

    # Create a simple SQLite table that exists in the backup
    conn = sqlite3.connect(legacy_db_path)
    conn.execute("CREATE TABLE legacy_data (id INTEGER PRIMARY KEY, content TEXT)")
    conn.execute("INSERT INTO legacy_data (content) VALUES ('Precious Golden Fund Data')")
    conn.commit()
    conn.close()

    print(f"1. Mock Legacy Backup created at {legacy_db_path}")

    # 2. Simulate setup_dev.py restoration logic
    print("2. Restoring from backup...")
    shutil.copy2(legacy_db_path, MOCK_CONFIG / "atlastrinity.db")
    print(f"   Data restored to {MOCK_CONFIG / 'atlastrinity.db'}")

    # 3. Simulate DB Initialization and Schema Auto-fix
    print("3. Initializing and Auto-fixing schema...")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{MOCK_CONFIG}/atlastrinity.db"

    from src.brain.db.manager import db_manager

    # Initialize will trigger Base.metadata.create_all and verify_schema(fix=True)
    await db_manager.initialize()

    print("4. Verifying results...")

    # A. Check if legacy data still exists (Restoration Success)
    conn = sqlite3.connect(MOCK_CONFIG / "atlastrinity.db")
    res = conn.execute("SELECT content FROM legacy_data").fetchone()
    if res and res[0] == "Precious Golden Fund Data":
        print("SUCCESS: Legacy data preserved!")
    else:
        print("FAILURE: Legacy data lost or overwritten.")

    # B. Check if new tables were added (Migration Success)
    res = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_promotions'"
    ).fetchone()
    if res:
        print("SUCCESS: New table 'knowledge_promotions' added successfully!")
    else:
        print("FAILURE: New table 'knowledge_promotions' missing.")

    conn.close()
    print("--- Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(test_restoration_logic())
