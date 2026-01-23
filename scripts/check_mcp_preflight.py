#!/usr/bin/env python3
"""CLI to run MCP package preflight checks and exit non-zero on issues.

Usage:
  scripts/check_mcp_preflight.py [--config PATH]

Defaults to global config at ~/.config/atlastrinity/mcp/config.json or falls
back to project src/mcp_server/config.json when not found.
"""

import argparse
import os
import sys
from pathlib import Path

from src.brain.mcp_preflight import scan_mcp_config_for_package_issues


def run(config: str | None = None) -> int:
    # Resolve config path
    if config:
        cfg_path = Path(config)
    else:
        cfg_path = Path.home() / ".config" / "atlastrinity" / "mcp" / "config.json"
        if not cfg_path.exists():
            cfg_path = Path(__file__).resolve().parents[1] / "src" / "mcp_server" / "config.json"

    print(f"MCP preflight: scanning config {cfg_path}")
    pkg_issues = scan_mcp_config_for_package_issues(cfg_path)
    # System limits may be noisy in CI; check them separately and treat them as warnings by default
    from src.brain.mcp_preflight import check_system_limits

    sys_issues = check_system_limits()

    # Report package issues (considered fatal)
    if pkg_issues:
        print("Found MCP package issues:")
        import re

        for it in pkg_issues:
            print(f"  - {it}")
            # If it's a python importability issue, suggest installing via pip
            if "not importable" in it:
                m = re.search(r"python module ([a-zA-Z0-9_\.]+) not importable", it)
                if m:
                    mod = m.group(1)
                    print(
                        f"    💡 Try: pip install {mod} (in your venv) or change server to an npx/bunx implementation if available",
                    )
        return 1

    # No package issues. Handle system limits:
    if sys_issues:
        print("Detected system limits issues:")
        for it in sys_issues:
            print(f"  - {it}")
            print(
                "    ⚠️ System limit detected. On macOS you can increase via: sudo sysctl -w kern.maxproc=4096; sudo sysctl -w kern.maxprocperuid=2048; and increase ulimit -u in shell settings.",
            )
        if os.getenv("FAIL_ON_SYS_LIMITS") == "1":
            print(
                "Failing preflight because FAIL_ON_SYS_LIMITS=1 and system limits are inadequate.",
            )
            return 1
        else:
            print(
                "Continuing despite system limit warnings (set FAIL_ON_SYS_LIMITS=1 to fail on these)",
            )

    print("No MCP package issues found.")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Path to MCP config.json to scan", default=None)
    args = parser.parse_args()
    rc = run(args.config)
    sys.exit(rc)


if __name__ == "__main__":
    main()
