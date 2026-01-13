from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from mcp.server import FastMCP

try:
    from .config_loader import get_config_value

    VIBE_BINARY = get_config_value("vibe", "binary", "vibe")
    DEFAULT_TIMEOUT_S = float(get_config_value("vibe", "timeout_s", 300))
    MAX_OUTPUT_CHARS = int(get_config_value("vibe", "max_output_chars", 200000))
    DISALLOW_INTERACTIVE = bool(get_config_value("vibe", "disallow_interactive", True))
except Exception:
    VIBE_BINARY = "vibe"
    DEFAULT_TIMEOUT_S = 300.0
    MAX_OUTPUT_CHARS = 200000
    DISALLOW_INTERACTIVE = True


ALLOWED_SUBCOMMANDS = {
    "list-editors",
    "list-modules",
    "run",
    "enable",
    "disable",
    "install",
    "smart-plan",
    "ask",
    "agent-chat",
    "agent-reset",
    "agent-on",
    "agent-off",
    "self-healing-status",
    "self-healing-scan",
    "vibe-status",
    "vibe-continue",
    "vibe-cancel",
    "vibe-help",
    "eternal-engine",
    "screenshots",
    "tui",
}


server = FastMCP("vibe")


def _truncate(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n... [TRUNCATED] ..."


def _resolve_vibe_binary() -> Optional[str]:
    if os.path.isabs(VIBE_BINARY) and os.path.exists(VIBE_BINARY):
        return VIBE_BINARY
    return shutil.which(VIBE_BINARY)


def _run_vibe(
    argv: List[str],
    cwd: Optional[str],
    timeout_s: float,
    extra_env: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    env = os.environ.copy()
    if extra_env:
        env.update({k: str(v) for k, v in extra_env.items()})

    try:
        p = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=float(timeout_s),
            check=False,
        )
    except FileNotFoundError:
        return {
            "error": f"Vibe CLI not found: '{argv[0]}'. Ensure it is installed and on PATH (or set mcp.vibe.binary in config.yaml)."
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Vibe CLI timed out after {timeout_s}s", "command": argv}
    except Exception as e:
        return {"error": f"Vibe CLI execution failed: {e}", "command": argv}

    stdout = _truncate(p.stdout or "")
    stderr = _truncate(p.stderr or "")

    if p.returncode != 0:
        return {
            "error": "Vibe CLI returned non-zero exit code",
            "returncode": p.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "command": argv,
        }

    return {
        "success": True,
        "returncode": p.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "command": argv,
    }


@server.tool()
def vibe_which() -> Dict[str, Any]:
    vibe_path = _resolve_vibe_binary()
    if not vibe_path:
        return {"error": f"Vibe CLI not found on PATH (binary='{VIBE_BINARY}')"}
    return {"success": True, "binary": vibe_path}


@server.tool()
def vibe_execute(
    subcommand: str,
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    timeout_s: Optional[float] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    vibe_path = _resolve_vibe_binary()
    if not vibe_path:
        return {"error": f"Vibe CLI not found on PATH (binary='{VIBE_BINARY}')"}

    sub = (subcommand or "").strip()
    if not sub:
        return {"error": "Missing subcommand"}

    if sub not in ALLOWED_SUBCOMMANDS:
        return {
            "error": f"Subcommand not allowed: '{sub}'. Allowed: {sorted(ALLOWED_SUBCOMMANDS)}",
        }

    if DISALLOW_INTERACTIVE and sub in {"tui"}:
        return {"error": "Interactive Vibe subcommand is disabled in MCP (tui)."}

    argv: List[str] = [vibe_path, sub]
    if args:
        argv.extend([str(a) for a in args])

    eff_timeout = (
        float(timeout_s) if timeout_s is not None else float(DEFAULT_TIMEOUT_S)
    )
    return _run_vibe(argv=argv, cwd=cwd, timeout_s=eff_timeout, extra_env=env)


@server.tool()
def vibe_agent_chat(
    message: str, cwd: Optional[str] = None, timeout_s: Optional[float] = None
) -> Dict[str, Any]:
    return vibe_execute(
        subcommand="agent-chat",
        args=["-p", message],
        cwd=cwd,
        timeout_s=timeout_s,
    )


@server.tool()
def vibe_smart_plan(
    query: str,
    editor: Optional[str] = None,
    cwd: Optional[str] = None,
    timeout_s: Optional[float] = None,
) -> Dict[str, Any]:
    args: List[str] = ["--query", query]
    if editor:
        args.extend(["--editor", editor])
    return vibe_execute(
        subcommand="smart-plan", args=args, cwd=cwd, timeout_s=timeout_s
    )


@server.tool()
def vibe_self_healing_status(
    cwd: Optional[str] = None, timeout_s: Optional[float] = None
) -> Dict[str, Any]:
    return vibe_execute(
        subcommand="self-healing-status", args=[], cwd=cwd, timeout_s=timeout_s
    )


@server.tool()
def vibe_self_healing_scan(
    cwd: Optional[str] = None, timeout_s: Optional[float] = None
) -> Dict[str, Any]:
    return vibe_execute(
        subcommand="self-healing-scan", args=[], cwd=cwd, timeout_s=timeout_s
    )


if __name__ == "__main__":
    server.run()
