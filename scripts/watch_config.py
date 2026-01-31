#!/usr/bin/env python3
"""
Configuration Watcher & Auto-Sync
Monitors `config/*.template` files and automatically syncs them to `~/.config/atlastrinity/`
preserving variable substitutions.
"""

import os
import shutil
import sys
import time
from pathlib import Path

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("Error: 'watchdog' module not found. Please run: pip install watchdog")
    sys.exit(1)

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_SRC = PROJECT_ROOT / "config"
CONFIG_DST_ROOT = Path.home() / ".config" / "atlastrinity"

# Mappings (Template Filename -> Destination Relative Path)
MAPPINGS: dict[str, str] = {
    "config.yaml.template": "config.yaml",
    "behavior_config.yaml.template": "behavior_config.yaml",
    "vibe_config.toml.template": "vibe_config.toml",
    "vibe/agents/accept-edits.toml.template": "vibe/agents/accept-edits.toml",
    "vibe/agents/auto-approve.toml.template": "vibe/agents/auto-approve.toml",
    "vibe/agents/plan.toml.template": "vibe/agents/plan.toml",

    "mcp_servers.json.template": "mcp/config.json",
    "prometheus.yml.template": "prometheus.yml",
}

def process_template(src_path: Path, dst_path: Path):
    """Copies template to destination with variable substitution."""
    try:
        if not src_path.exists():
            return

        with open(src_path, encoding="utf-8") as f:
            content = f.read()

        # Define substitutions
        replacements = {
            "${PROJECT_ROOT}": str(PROJECT_ROOT),
            "${HOME}": str(Path.home()),
            "${CONFIG_ROOT}": str(CONFIG_DST_ROOT),
            "${PYTHONPATH}": str(PROJECT_ROOT),
            "${GITHUB_TOKEN}": os.getenv("GITHUB_TOKEN", "${GITHUB_TOKEN}"),
        }

        for key, value in replacements.items():
            content = content.replace(key, value)

        # Ensure dir exists
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[{time.strftime('%H:%M:%S')}] Synced: {src_path.name} -> {dst_path.name}")

    except Exception as e:
        print(f"Error syncing {src_path.name}: {e}")

class ConfigHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Get relative path from config source
        try:
            rel_path = Path(event.src_path).relative_to(CONFIG_SRC)
            filename = str(rel_path)
        except ValueError:
            return

        if filename in MAPPINGS:
            dst_rel = MAPPINGS[filename]
            dst_path = CONFIG_DST_ROOT / dst_rel
            # Add a small delay to ensure write verify
            time.sleep(0.1) 
            process_template(Path(event.src_path), dst_path)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Watch or sync configs")
    parser.add_argument("--sync-only", action="store_true", help="Sync once and exit")
    args = parser.parse_args()

    print("Starting AtlasTrinity Config Sync...")
    print(f"Watching: {CONFIG_SRC}")
    print(f"Target:   {CONFIG_DST_ROOT}")
    print("-" * 40)
    
    # Initial sync
    print("Performing sync...")
    for tpl, dst in MAPPINGS.items():
        src = CONFIG_SRC / tpl
        if src.exists():
            process_template(src, CONFIG_DST_ROOT / dst)
    print("Sync completed.")
    print("-" * 40)

    if args.sync_only:
        return

    print("Entering watch mode...")
    event_handler = ConfigHandler()
    observer = Observer()
    observer.schedule(event_handler, str(CONFIG_SRC), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main()
