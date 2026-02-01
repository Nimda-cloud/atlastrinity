#!/usr/bin/env python3
"""
Clean Backups
Removes the backups/databases directory.
"""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = PROJECT_ROOT / "backups" / "databases"

def clean_backups():
    print("🧹 Cleaning Backups...")
    if BACKUP_DIR.exists():
        try:
            shutil.rmtree(BACKUP_DIR)
            print(f"✅ Deleted {BACKUP_DIR}")
        except Exception as e:
            print(f"❌ Failed to delete {BACKUP_DIR}: {e}")
    else:
        print(f"ℹ️ {BACKUP_DIR} not found.")

if __name__ == "__main__":
    clean_backups()
