"""
AtlasTrinity Manual Full Backup
Triggered via 'npm run backup:all'
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from scripts.setup_dev import backup_databases

    backup_databases()
except Exception as e:
    print(f"Failed to execute backup: {e}")
    sys.exit(1)
