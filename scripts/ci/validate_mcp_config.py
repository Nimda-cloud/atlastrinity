#!/usr/bin/env python3
"""
Validate MCP configuration file against schema.
Ensures all required fields are present and types are correct.
"""

import json
import sys
from pathlib import Path
from typing import Any


def validate_server_config(name: str, config: dict[str, Any]) -> list[str]:
    """Validate a single server configuration."""
    errors = []

    # Required fields
    if "command" not in config:
        errors.append(f"{name}: Missing required field 'command'")

    # Optional but important fields
    if "description" not in config:
        errors.append(f"{name}: Missing 'description' (recommended)")

    # Validate tier if present
    if "tier" in config:
        if not isinstance(config["tier"], int) or config["tier"] not in [1, 2, 3, 4]:
            errors.append(f"{name}: Invalid tier value, must be 1-4")

    # Validate agents if present
    if "agents" in config:
        if not isinstance(config["agents"], list):
            errors.append(f"{name}: 'agents' must be a list")
        else:
            valid_agents = {"atlas", "tetyana", "grisha"}
            for agent in config["agents"]:
                if agent not in valid_agents:
                    errors.append(f"{name}: Invalid agent '{agent}', must be one of {valid_agents}")

    # Validate environment variables format
    if "env" in config:
        if not isinstance(config["env"], dict):
            errors.append(f"{name}: 'env' must be a dictionary")

    return errors


def validate_mcp_config(config_path: Path) -> bool:
    """Validate the entire MCP configuration file."""
    print(f"🔍 Validating MCP config: {config_path}")

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False

    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False

    # Validate top-level structure
    if "mcpServers" not in config:
        print("❌ Missing 'mcpServers' key")
        return False

    servers = config["mcpServers"]
    all_errors = []
    server_count = 0

    # Validate each server
    for name, server_config in servers.items():
        # Skip comment keys
        if name.startswith("_comment"):
            continue

        server_count += 1
        errors = validate_server_config(name, server_config)
        all_errors.extend(errors)

    # Report results
    if all_errors:
        print(f"\n❌ Found {len(all_errors)} validation error(s):")
        for error in all_errors:
            print(f"  - {error}")
        return False
    else:
        print(f"✅ Configuration valid: {server_count} servers configured")

        # Count by tier
        tier_counts = {}
        disabled_count = 0
        for name, cfg in servers.items():
            if name.startswith("_comment"):
                continue
            tier = cfg.get("tier", 0)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            if cfg.get("disabled", False):
                disabled_count += 1

        print(f"📊 Tier breakdown: {dict(sorted(tier_counts.items()))}")
        print(f"🔒 Disabled servers: {disabled_count}")

        return True


def main():
    """Main entry point."""
    # Check both project and global config
    project_root = Path(__file__).parent.parent.parent
    configs_to_check = [
        project_root / "src" / "mcp_server" / "config.json",
    ]

    all_valid = True
    for config_path in configs_to_check:
        if config_path.exists():
            if not validate_mcp_config(config_path):
                all_valid = False
            print()

    if all_valid:
        print("✅ All MCP configurations are valid")
        sys.exit(0)
    else:
        print("❌ MCP configuration validation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
