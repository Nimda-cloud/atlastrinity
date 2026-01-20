#!/usr/bin/env python3
"""Helper script to initialize database during setup"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.brain.db.manager import db_manager


async def main():
    """Initialize and close database"""
    try:
        await db_manager.initialize()
        await db_manager.close()
        print("[DB] Database initialized successfully.", flush=True)
    except Exception as e:
        print(f"[DB] Error: {e}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
