#!/usr/bin/env python3
"""
Comprehensive Backup Script for AtlasTrinity
Backs up all databases, vectors, and knowledge graphs from local config to repository.
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

# Sources
CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = PROJECT_ROOT / "backups" / "databases"

# Mappings (Source -> Backup Destination)
PATHS_TO_BACKUP = [
    (CONFIG_ROOT / "atlastrinity.db", BACKUP_DIR / "atlastrinity.db"),
    (CONFIG_ROOT / "data" / "golden_fund", BACKUP_DIR / "golden_fund"),
    (CONFIG_ROOT / "memory" / "chroma", BACKUP_DIR / "memory" / "chroma"),
]

def backup_all():
    print(f"--- 🔱 AtlasTrinity Full Backup Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    if not CONFIG_ROOT.exists():
        print(f"Error: Config root not found at {CONFIG_ROOT}")
        return False

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    total_count = len(PATHS_TO_BACKUP)

    for src, dst in PATHS_TO_BACKUP:
        if not src.exists():
            print(f"⚠️ Source not found, skipping: {src}")
            continue

        try:
            # Create destination parent directory
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            if src.is_file():
                shutil.copy2(src, dst)
                print(f"✅ Backed up File: {src.name} -> {dst.relative_to(PROJECT_ROOT)}")
            elif src.is_dir():
                # For directories, we sync content
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"✅ Backed up Directory: {src.name}/ -> {dst.relative_to(PROJECT_ROOT)}")
            
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to backup {src.name}: {e}")

    print(f"\n🎉 Backup complete: {success_count}/{total_count} items synced to repository.")
    return success_count > 0

if __name__ == "__main__":
    success = backup_all()
    sys.exit(0 if success else 1)
