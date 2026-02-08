"""
Force reload AtlasTrinity configuration
"""

import importlib
import os
import sys


def force_reload_config():
    """Force reload configuration"""

    print("🔄 Force reloading configuration...")

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
    print(f"tool_routing keys: {list(tool_routing.keys())}")

    if "macos_use" in tool_routing:
        print("✅ macos_use found in tool_routing")
        macos_config = tool_routing["macos_use"]
        print(f"macos_use synonyms: {macos_config.get('synonyms', [])}")
        return True
    print("❌ macos_use not found in tool_routing")
    return False

if __name__ == "__main__":
    force_reload_config()
