"""
Reload AtlasTrinity configuration
"""

import os
import shutil
import subprocess
import time


def reload_atlastrinity_config():
    """Reload AtlasTrinity configuration"""

    # Kill existing processes
    subprocess.run(["pkill", "-f", "npm run dev"], check=False)
    subprocess.run(["pkill", "-f", "python.*main.py"], check=False)

    time.sleep(2)

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
            shutil.rmtree(cache_dir, ignore_errors=True)

    # Verify configuration
    config_file = os.path.join(CONFIG_DIR, "behavior_config.yaml")

    if os.path.exists(config_file):
        with open(config_file) as f:
            content = f.read()

        if "macos-use_get_clipboard: macos-use_get_clipboard" in content:
            pass
        else:
            return False
    else:
        return False

    return True


if __name__ == "__main__":
    reload_atlastrinity_config()
