"""
Clean Backups
Removes the backups/databases directory.
"""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKUP_DIR = PROJECT_ROOT / "backups" / "databases"


def clean_backups():
    if BACKUP_DIR.exists():
        try:
            shutil.rmtree(BACKUP_DIR)
        except Exception:
            pass
    else:
        pass


if __name__ == "__main__":
    clean_backups()
