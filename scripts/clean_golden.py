#!/usr/bin/env python3
"""
Clean Golden Fund Data
Removes local Golden Fund data files.
"""

import shutil
from pathlib import Path

CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"
GOLDEN_FUND_LIVE = CONFIG_ROOT / "data" / "golden_fund"


def clean_golden_fund():
    print("🧹 Cleaning Golden Fund Data...")

    if GOLDEN_FUND_LIVE.exists():
        try:
            shutil.rmtree(GOLDEN_FUND_LIVE)
            print(f"✅ Deleted {GOLDEN_FUND_LIVE}")
        except Exception as e:
            print(f"❌ Failed to delete {GOLDEN_FUND_LIVE}: {e}")
            return False
    else:
        print("ℹ️ Golden Fund dir not found (already clean).")

    return True


if __name__ == "__main__":
    clean_golden_fund()
