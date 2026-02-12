"""
Clean Golden Fund Data
Removes local Golden Fund data files.
"""

import shutil
from pathlib import Path

CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"
GOLDEN_FUND_LIVE = CONFIG_ROOT / "data" / "golden_fund"


def clean_golden_fund():

    targets = [
        GOLDEN_FUND_LIVE,
        CONFIG_ROOT / "data" / "search",
        CONFIG_ROOT / "memory" / "chroma",
    ]

    for target in targets:
        if target.exists():
            try:
                if target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
            except Exception:
                pass
        else:
            pass

    return True


if __name__ == "__main__":
    clean_golden_fund()
