#!/usr/bin/env python3
"""
Provider Switch Utility
======================

Easy switching between Copilot and Windsurf providers.

Usage:
    python scripts/switch_provider.py windsurf
    python scripts/switch_provider.py copilot
    python scripts/switch_provider.py --status
"""

import shutil
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_current_provider():
    """Get current provider from global config."""
    config_path = Path.home() / ".config" / "atlastrinity" / "config.yaml"

    if not config_path.exists():
        return "unknown"

    try:
        import yaml

        with open(config_path) as f:
            config = yaml.safe_load(f)
        return config.get("models", {}).get("provider", "unknown")
    except:
        return "unknown"


def switch_to_windsurf():
    """Switch configuration to Windsurf provider."""
    config_path = Path.home() / ".config" / "atlastrinity" / "config.yaml"
    vibe_path = Path.home() / ".config" / "atlastrinity" / "vibe_config.toml"

    # Backup current configs
    if config_path.exists():
        shutil.copy2(config_path, config_path.with_suffix(".yaml.backup"))
    if vibe_path.exists():
        shutil.copy2(vibe_path, vibe_path.with_suffix(".toml.backup"))

    # Update main config
    try:
        import yaml

        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

        # Update models section
        if "models" not in config:
            config["models"] = {}

        config["models"]["provider"] = "windsurf"
        config["models"]["default"] = "deepseek-v3"
        config["models"]["vision"] = "deepseek-v3"
        config["models"]["reasoning"] = "deepseek-r1"
        config["models"]["code_analysis"] = "deepseek-v3"
        config["models"]["consolidation"] = "deepseek-v3"
        config["models"]["fallback"] = "deepseek-v3"
        config["models"]["sandbox"] = "deepseek-v3"

        # Update agents
        if "agents" not in config:
            config["agents"] = {}

        config["agents"]["atlas"] = {
            "deep_model": "deepseek-r1",
            "temperature": 0.7,
            "max_tokens": 2000,
            "max_tokens_deep": 12000,
        }

        config["agents"]["tetyana"] = {
            "reasoning_model": "deepseek-r1",
            "vision_model": "deepseek-v3",
            "temperature": 0.5,
            "max_tokens": 2000,
        }

        config["agents"]["grisha"] = {
            "strategy_model": "deepseek-r1",
            "vision_model": "deepseek-v3",
            "verdict_model": "deepseek-r1",
            "temperature": 0.3,
            "max_tokens": 1500,
        }

        # Update MCP sequential thinking
        if "mcp" not in config:
            config["mcp"] = {}

        config["mcp"]["sequential_thinking"] = {"enabled": True, "model": "deepseek-r1"}

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    except Exception:
        return False

    # Update Vibe config
    try:
        import toml

        with open(vibe_path) as f:
            vibe_config = toml.load(f)

        vibe_config["active_model"] = "deepseek-v3"

        with open(vibe_path, "w") as f:
            toml.dump(vibe_config, f)

    except Exception:
        return False

    return True


def switch_to_copilot():
    """Switch configuration to Copilot provider."""
    config_path = Path.home() / ".config" / "atlastrinity" / "config.yaml"
    vibe_path = Path.home() / ".config" / "atlastrinity" / "vibe_config.toml"

    # Backup current configs
    if config_path.exists():
        shutil.copy2(config_path, config_path.with_suffix(".yaml.backup"))
    if vibe_path.exists():
        shutil.copy2(vibe_path, vibe_path.with_suffix(".toml.backup"))

    # Update main config
    try:
        import yaml

        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

        # Update models section
        if "models" not in config:
            config["models"] = {}

        config["models"]["provider"] = "copilot"
        config["models"]["default"] = "gpt-4o"
        config["models"]["vision"] = "gpt-4o"
        config["models"]["reasoning"] = "oswe-vscode-secondary"
        config["models"]["code_analysis"] = "grok-code-fast-1"
        config["models"]["consolidation"] = "oswe-vscode-secondary"
        config["models"]["fallback"] = "gpt-4o"
        config["models"]["sandbox"] = "oswe-vscode-secondary"

        # Update agents
        if "agents" not in config:
            config["agents"] = {}

        config["agents"]["atlas"] = {
            "deep_model": "oswe-vscode-secondary",
            "temperature": 0.7,
            "max_tokens": 2000,
            "max_tokens_deep": 12000,
        }

        config["agents"]["tetyana"] = {
            "reasoning_model": "gpt-4.1",
            "vision_model": "gpt-4o",
            "temperature": 0.5,
            "max_tokens": 2000,
        }

        config["agents"]["grisha"] = {
            "strategy_model": "oswe-vscode-secondary",
            "vision_model": "gpt-4o",
            "verdict_model": "oswe-vscode-secondary",
            "temperature": 0.3,
            "max_tokens": 1500,
        }

        # Update MCP sequential thinking
        if "mcp" not in config:
            config["mcp"] = {}

        config["mcp"]["sequential_thinking"] = {"enabled": True, "model": "oswe-vscode-secondary"}

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    except Exception:
        return False

    # Update Vibe config
    try:
        import toml

        with open(vibe_path) as f:
            vibe_config = toml.load(f)

        vibe_config["active_model"] = "gpt-4.1"

        with open(vibe_path, "w") as f:
            toml.dump(vibe_config, f)

    except Exception:
        return False

    return True


def show_status():
    """Show current provider configuration."""
    get_current_provider()

    config_path = Path.home() / ".config" / "atlastrinity" / "config.yaml"
    vibe_path = Path.home() / ".config" / "atlastrinity" / "vibe_config.toml"

    if config_path.exists():
        try:
            import yaml

            with open(config_path) as f:
                config = yaml.safe_load(f)

            config.get("models", {})

        except Exception:
            pass

    if vibe_path.exists():
        try:
            import toml

            with open(vibe_path) as f:
                toml.load(f)

        except Exception:
            pass


def main():
    if len(sys.argv) < 2:
        show_status()
        return

    action = sys.argv[1].lower()

    if action == "--status":
        show_status()
    elif action == "windsurf":
        if switch_to_windsurf():
            pass
        else:
            pass
    elif action == "copilot":
        if switch_to_copilot():
            pass
        else:
            pass
    else:
        pass


if __name__ == "__main__":
    main()
