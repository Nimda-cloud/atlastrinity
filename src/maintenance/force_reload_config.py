"""
Force reload AtlasTrinity configuration
"""

import importlib
import os
import sys


def force_reload_config():
    """Force reload configuration"""

    # Add src to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

    # Clear config cache
    sys.modules.pop("brain.config_loader", None)
    sys.modules.pop("brain.behavior_engine", None)

    # Reload modules
    from brain.config_loader import config

    importlib.reload(sys.modules["brain.config_loader"])

    # Check config
    tool_routing = config.get("tool_routing", {})

    if "macos_use" in tool_routing:
        tool_routing["macos_use"]
        return True
    return False


if __name__ == "__main__":
    force_reload_config()
