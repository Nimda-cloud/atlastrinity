"""
Backup Golden Fund Database
Copies the live database and analysis cache to the repository backup location.
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

# Paths
CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"
GOLDEN_FUND_LIVE = CONFIG_ROOT / "data" / "golden_fund"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_FUND_BACKUP = PROJECT_ROOT / "backups" / "databases" / "golden_fund"


def backup_golden_fund():
    print("--- Golden Fund Backup ---")

    if not GOLDEN_FUND_LIVE.exists():
        print(f"Error: Live data not found at {GOLDEN_FUND_LIVE}")
        return False

    GOLDEN_FUND_BACKUP.mkdir(parents=True, exist_ok=True)

    # 1. Backup SQLite DB
    db_file = GOLDEN_FUND_LIVE / "golden.db"
    if db_file.exists():
        backup_file = GOLDEN_FUND_BACKUP / "golden.db"
        try:
            shutil.copy2(db_file, backup_file)
            print(f"✅ Database backed up to {backup_file}")
        except Exception as e:
            print(f"❌ Failed to backup database: {e}")
            return False
    else:
        print("⚠️ No golden.db found to backup")

    # 2. Backup Analysis Cache (JSON files)
    # Recursively copy the analysis_cache folder
    live_cache = GOLDEN_FUND_LIVE / "analysis_cache"
    if live_cache.exists():
        backup_cache = GOLDEN_FUND_BACKUP / "analysis_cache"
        try:
            # Remove old backup cache to ensure exact sync
            if backup_cache.exists():
                shutil.rmtree(backup_cache)
            shutil.copytree(live_cache, backup_cache)
            print(f"✅ Analysis cache backed up to {backup_cache}")
        except Exception as e:
            print(f"❌ Failed to backup cache: {e}")
            return False

    print(f"🎉 Backup complete at {datetime.now()}")
    return True


if __name__ == "__main__":
    success = backup_golden_fund()
    sys.exit(0 if success else 1)
