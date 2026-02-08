"""
Clean Main System Data (Learning & Experience)
Removes atlastrinity.db and memory chroma vectors.
"""

import shutil
from pathlib import Path

CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"

def clean_main():
    print("🧹 Cleaning Main System Experience (Learning, DB, Memory)...")

    targets = [
        CONFIG_ROOT / "atlastrinity.db",
        CONFIG_ROOT / "data" / "monitoring.db",
        CONFIG_ROOT / "data" / "trinity.db",
        CONFIG_ROOT / "memory",
        CONFIG_ROOT / "logs",
        CONFIG_ROOT / "cache",
        CONFIG_ROOT / "data",  # ← All data (search, analysis, etc.)
        CONFIG_ROOT / "mcp",  # ← All MCP configs
        CONFIG_ROOT / "vibe",  # ← Vibe agents folder
        CONFIG_ROOT / "config.yaml",
        CONFIG_ROOT / "behavior_config.yaml",
        CONFIG_ROOT / "vibe_config.toml",
        CONFIG_ROOT / "prometheus.yml",
    ]

    for target in targets:
        if target.exists():
            try:
                if target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
                print(f"✅ Deleted {target}")
            except Exception as e:
                print(f"❌ Failed to delete {target}: {e}")
        else:
            print(f"ℹ️ {target.name} not found.")

    return True

if __name__ == "__main__":
    clean_main()
