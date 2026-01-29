#!/usr/bin/env python3
"""
Reload AtlasTrinity configuration
"""

import os
import sys
import time


def reload_atlastrinity_config():
    """Reload AtlasTrinity configuration"""

    print("🔄 Reloading AtlasTrinity configuration...")

    # Kill existing processes
    print("🛑 Stopping existing processes...")
    os.system("pkill -f 'npm run dev' || true")
    os.system("pkill -f 'python.*main.py' || true")

    time.sleep(2)

    # Clear any caches
    print("🧹 Clearing caches...")
    
    # Define paths dynamically
    HOME = os.path.expanduser("~")
    PROJECT_ROOT = os.path.join(HOME, "Documents/GitHub/atlastrinity")
    CONFIG_DIR = os.path.join(HOME, ".config/atlastrinity")
    
    cache_dirs = [
        os.path.join(CONFIG_DIR, "__pycache__"),
        os.path.join(PROJECT_ROOT, "__pycache__"),
        os.path.join(PROJECT_ROOT, "src/__pycache__"),
    ]

    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            os.system(f"rm -rf {cache_dir}")
            print(f"✅ Cleared {cache_dir}")

    # Verify configuration
    print("🔍 Verifying configuration...")
    config_file = os.path.join(CONFIG_DIR, "behavior_config.yaml")

    if os.path.exists(config_file):
        with open(config_file) as f:
            content = f.read()

        if "macos-use_get_clipboard: macos-use_get_clipboard" in content:
            print("✅ Configuration contains macos-use_get_clipboard mapping")
        else:
            print("❌ Configuration missing macos-use_get_clipboard mapping")
            return False
    else:
        print("❌ Configuration file not found")
        return False

    print("🎉 Configuration reload completed!")
    return True


if __name__ == "__main__":
    reload_atlastrinity_config()
