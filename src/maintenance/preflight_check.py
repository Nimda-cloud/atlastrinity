"""CLI to run MCP package preflight checks and exit non-zero on issues.

Usage:
  scripts/check_mcp_preflight.py [--config PATH]

Defaults to global config at ~/.config/atlastrinity/mcp/config.json or falls
back to project config/mcp_servers.json.template when not found.
"""

import argparse
import os
import sys
from pathlib import Path

from src.brain.mcp.mcp_preflight import scan_mcp_config_for_package_issues


def run(config: str | None = None) -> int:
    # Resolve config path
    if config:
        cfg_path = Path(config)
    else:
        cfg_path = Path.home() / ".config" / "atlastrinity" / "mcp" / "config.json"
        if not cfg_path.exists():
            cfg_path = Path(__file__).resolve().parents[1] / "config" / "mcp_servers.json.template"

    pkg_issues = scan_mcp_config_for_package_issues(cfg_path)
    # System limits may be noisy in CI; check them separately and treat them as warnings by default
    from src.brain.mcp.mcp_preflight import check_system_limits

    sys_issues = check_system_limits()

    # Report package issues (considered fatal)
    if pkg_issues:
        import re

        for it in pkg_issues:
            # If it's a python importability issue, suggest installing via pip
            if "not importable" in it:
                m = re.search(r"python module ([a-zA-Z0-9_\.]+) not importable", it)
                if m:
                    m.group(1)
        return 1

    # No package issues. Handle system limits:
    if sys_issues:
        for it in sys_issues:
            pass
        if os.getenv("FAIL_ON_SYS_LIMITS") == "1":
            return 1

    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Path to MCP config.json to scan", default=None)
    args = parser.parse_args()
    rc = run(args.config)
    sys.exit(rc)


if __name__ == "__main__":
    main()
