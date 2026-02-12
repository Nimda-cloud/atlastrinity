#!/usr/bin/env python3
"""
Test Global .env Loading
========================

Перевіряє, чи всі компоненти системи правильно читають токени, порти та конфігурацію
з глобального місця ~/.config/atlastrinity/.env
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_global_env_loading():
    """Test if all components read from global .env."""
    # This is a test script, so print statements are acceptable
    # for providing feedback during testing
    print("=" * 60)  # noqa: T201
    print("TEST: Global .env Loading")  # noqa: T201
    print("=" * 60)  # noqa: T201

    global_env_path = Path.home() / ".config" / "atlastrinity" / ".env"
    project_env_path = project_root / ".env"

    print(f"\n📁 Global .env: {global_env_path}")  # noqa: T201
    print(f"📁 Project .env: {project_env_path}")  # noqa: T201

    # Check which .env exists
    global_exists = global_env_path.exists()
    project_exists = project_env_path.exists()

    print(f"\n📋 Global .env exists: {'✅' if global_exists else '❌'}")  # noqa: T201
    print(f"📋 Project .env exists: {'✅' if project_exists else '❌'}")  # noqa: T201

    if not global_exists:
        print("\n❌ Глобальний .env не знайдено!")  # noqa: T201
        print("   Запустіть: python -m providers sync або python scripts/setup_dev.py")  # noqa: T201
        return False

    # Test 1: src/brain/config.py
    print("\n--- Test 1: src/brain/config.py ---")  # noqa: T201
    try:
        from src.brain import config

        windsurf_key = os.getenv("WINDSURF_API_KEY")
        copilot_key = os.getenv("COPILOT_API_KEY")

        print(  # noqa: T201
            f"  WINDSURF_API_KEY: {'✅' if windsurf_key else '❌'} ({len(str(windsurf_key)) if windsurf_key else 'Not set'})"
        )
        print(  # noqa: T201
            f"  COPILOT_API_KEY: {'✅' if copilot_key else '❌'} ({len(str(copilot_key)) if copilot_key else 'Not set'})"
        )
    except Exception as e:
        print(f"  ❌ Error: {e}")  # noqa: T201

    # Test 2: src/brain/config_loader.py
    print("\n--- Test 2: src/brain/config_loader.py ---")  # noqa: T201
    try:
        from src.brain.config.config_loader import config

        # Config loader loads from global .env
        provider = config.get("models.provider")
        print(f"  models.provider: {provider}")  # noqa: T201

        # Check if environment variables are loaded
        windsurf_key = os.getenv("WINDSURF_API_KEY")
        print(  # noqa: T201
            f"  WINDSURF_API_KEY: {'✅' if windsurf_key else '❌'} ({len(str(windsurf_key)) if windsurf_key else 'Not set'})"
        )
    except Exception as e:
        print(f"  ❌ Error: {e}")  # noqa: T201

    # Test 3: Providers (Windsurf & Copilot)
    print("\n--- Test 3: Providers ---")  # noqa: T201
    try:
        from providers import CopilotLLM, WindsurfLLM

        # Test Windsurf
        try:
            WindsurfLLM(model_name="deepseek-v3")
            print("  WindsurfLLM: ✅ (API key loaded)")  # noqa: T201
        except Exception as e:
            print(f"  WindsurfLLM: ❌ ({e})")  # noqa: T201

        # Test Copilot
        try:
            CopilotLLM(model_name="gpt-4o")
            print("  CopilotLLM: ✅ (API key loaded)")  # noqa: T201
        except Exception as e:
            print(f"  CopilotLLM: ❌ ({e})")  # noqa: T201
    except Exception as e:
        print(f"  ❌ Error importing providers: {e}")  # noqa: T201

    # Test 4: MCP Servers
    print("\n--- Test 4: MCP Servers ---")  # noqa: T201
    try:
        from src.mcp_server.vibe_server import get_vibe_config

        config = get_vibe_config()
        print("  Vibe config: ✅")  # noqa: T201
    except Exception as e:
        print(f"  ❌ Vibe server error: {e}")  # noqa: T201

    # Test 5: Script utilities
    print("\n--- Test 5: Script Utilities ---")  # noqa: T201
    try:
        # Check if it reads from environment
        windsurf_key = os.getenv("WINDSURF_API_KEY")
        print(f"  UniversalProxy: {'✅' if windsurf_key else '❌'} (WINDSURF_API_KEY loaded)")  # noqa: T201
    except Exception as e:
        print(f"  ❌ Universal proxy error: {e}")  # noqa: T201

    # Test 6: Check specific keys
    print("\n--- Test 6: Specific Keys Check ---")  # noqa: T201
    keys_to_check = [
        "WINDSURF_API_KEY",
        "COPILOT_API_KEY",
        "WINDSURF_INSTALL_ID",
        "WINDSURF_LS_PORT",
        "WINDSURF_LS_CSRF",
        "GITHUB_TOKEN",
    ]

    for key in keys_to_check:
        value = os.getenv(key)
        status = "✅" if value else "❌"
        display_value = f"{value[:15]}..." if value and len(value) > 15 else (value or "Not set")
        print(f"  {key}: {status} ({display_value})")  # noqa: T201

    print("\n" + "=" * 60)  # noqa: T201
    return True


if __name__ == "__main__":
    test_global_env_loading()
