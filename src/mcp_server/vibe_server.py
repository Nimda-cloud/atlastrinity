"""Vibe MCP Server - Hyper-Refactored Implementation

This server wraps the Mistral Vibe CLI in MCP-compliant programmatic mode.
Fully aligned with official Mistral Vibe documentation and configuration.

Key Features:
- Full configuration support (providers, models, agents, tool permissions)
- 17 MCP tools covering all Vibe capabilities
- Streaming output with real-time notifications
- Proper error handling and resource cleanup
- Session persistence and resumption
- Dynamic model/provider switching

Based on official Mistral Vibe documentation:
https://docs.mistral.ai/vibe/configuration/

Author: AtlasTrinity Team
Date: 2026-01-20
Version: 3.0 (Hyper-Refactored)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from re import Pattern
from typing import Any, Literal, cast

from mcp.server import FastMCP
from mcp.server.fastmcp import Context

from .vibe_config import (
    AgentMode,
    ProviderConfig,
    VibeConfig,
)

# =============================================================================
# SETUP: Logging, Configuration, Constants
# =============================================================================

# ANSI escape code pattern for stripping colors
ANSI_ESCAPE: Pattern = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Default config root (fallback if config_loader fails)
DEFAULT_CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"

# TUI artifacts to filter out from logs
SPAM_TRIGGERS = [
    "Welcome to",
    "│",
    "╭",
    "╮",
    "╰",
    "─",
    "──",
    "[2K",
    "[1A",
    "Press Enter",
    "↵",
    "ListToolsRequest",
    "Processing request of type",
    "Secure MCP Filesystem Server",
    "Client does not support MCP Roots",
    "Resolving dependencies",
    "Resolved, downloaded and extracted",
    "Saved lockfile",
    "Sequential Thinking MCP Server",
    "Starting Context7 MCP Server",
    "Context7 MCP Server connected via stdio",
    "Redis connected via URL",
    "Lessons:",
    "Strategies:",
    "Discoveries:",
    "brain - INFO - [MEMORY]",
    "brain - INFO - [STATE]",
]

logger = logging.getLogger("vibe_mcp")
logger.setLevel(logging.DEBUG)

# Setup file and stream handlers
try:
    log_dir = DEFAULT_CONFIG_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # File handler
    fh = logging.FileHandler(log_dir / "vibe_server.log", mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ),
    )
    logger.addHandler(fh)
except Exception as e:
    print(f"[VIBE] Warning: Could not setup file logging: {e}")

sh = logging.StreamHandler(sys.stderr)
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter("[VIBE_MCP] %(levelname)s: %(message)s"))
logger.addHandler(sh)

# Load configuration
try:
    from .config_loader import CONFIG_ROOT, PROJECT_ROOT, get_config_value

    VIBE_BINARY: str = get_config_value("mcp.vibe", "binary", "vibe")
    # Timeout is now controlled by vibe_config.toml (eff_timeout logic)
    DEFAULT_TIMEOUT_S: float = 600.0
    MAX_OUTPUT_CHARS: int = int(get_config_value("mcp.vibe", "max_output_chars", 500000))
    VIBE_WORKSPACE = get_config_value("mcp.vibe", "workspace", str(CONFIG_ROOT / "vibe_workspace"))
    VIBE_CONFIG_FILE = get_config_value("mcp.vibe", "config_file", None)
    AGENT_MODEL_OVERRIDE = get_config_value("agents.tetyana", "model", None)

    if not AGENT_MODEL_OVERRIDE:
        logger.warning(
            "[VIBE] AGENT_MODEL_OVERRIDE not set in config, strict configuration enforced",
        )

except Exception:

    def get_config_value(section: str, key: str, default: Any = None) -> Any:
        return default

    VIBE_BINARY = "vibe"
    DEFAULT_TIMEOUT_S = 600.0
    MAX_OUTPUT_CHARS = 500000
    CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    VIBE_WORKSPACE = str(CONFIG_ROOT / "vibe_workspace")
    VIBE_CONFIG_FILE = None

# Derived paths
SYSTEM_ROOT = str(PROJECT_ROOT)
LOG_DIR = str(CONFIG_ROOT / "logs")
INSTRUCTIONS_DIR = str(Path(VIBE_WORKSPACE) / "instructions")
VIBE_SESSION_DIR = Path.home() / ".vibe" / "logs" / "session"
DATABASE_URL = get_config_value(
    "database",
    "url",
    f"sqlite+aiosqlite:///{CONFIG_ROOT}/atlastrinity.db",
)


# Allowed subcommands (CLI-only, no TUI)
ALLOWED_SUBCOMMANDS = {
    "list-editors",
    "list-modules",
    "run",
    "enable",
    "disable",
    "install",
    "smart-plan",
    "ask",
    "agent-reset",
    "agent-on",
    "agent-off",
    "vibe-status",
    "vibe-continue",
    "vibe-cancel",
    "vibe-help",
    "eternal-engine",
    "screenshots",
}

# Blocked subcommands (interactive TUI)
BLOCKED_SUBCOMMANDS = {"tui", "agent-chat", "self-healing-status", "self-healing-scan"}

# =============================================================================
# PLATFORM & DEVELOPMENT GUIDELINES
# =============================================================================

MACOS_DEVELOPMENT_GUIDELINES = """
MACOS DEVELOPMENT DOCTRINE:
- TARGET: macOS 13.0+ (Ventura).
- FRAMEWORK: SwiftUI (macOS specialized).
- UI MODIFIERS: Avoid iOS-specific modifiers like .navigationBarItems or .navigationBarTitle. Use .toolbar, .navigationTitle, and .navigationSubtitle.
- COLORS: Use platform-agnostic Color.secondary, Color.primary, or NSColor-linked colors. Avoid Color(.systemBackground) (iOS).
- CONCURRENCY: Strictly use @MainActor for SwiftUI Views and ViewModels.
- NETWORKING: Use Foundation URLSession or low-level Network.framework for macOS.
"""

DYNAMIC_VERIFICATION_PROTOCOL = """
DYNAMIC VERIFICATION PROTOCOL:
1. IDENTIFY Project Type:
   - .swift / Package.swift -> Swift Project
   - .py / requirements.txt -> Python Project
   - .js, .ts / package.json -> Node.js Project
2. EXECUTE Build/Check:
   - Swift: Run 'swift build' in the project root.
   - Python: Run 'python -m py_compile <file>' and 'ruff check <file>'.
   - Node.js: Run 'npm run build' or 'tsc'.
3. ANALYZE Output:
   - If exit code != 0, READ the error log, ANALYZE the message, and FIX it in the next iteration.
"""

# =============================================================================
# GLOBAL STATE
# =============================================================================

# Vibe configuration (loaded at startup)
_vibe_config: VibeConfig | None = None
_current_mode: AgentMode = AgentMode.AUTO_APPROVE
_current_model: str | None = None

# Concurrency Control (Queueing)
# Vibe is heavy on tokens and resources. We serialize calls to avoid Rate Limit collisions.
VIBE_LOCK = asyncio.Lock()
VIBE_QUEUE_SIZE = 0


def get_vibe_config() -> VibeConfig:
    """Get or load the Vibe configuration."""
    global _vibe_config
    if _vibe_config is None:
        config_path = Path(VIBE_CONFIG_FILE) if VIBE_CONFIG_FILE else None
        _vibe_config = VibeConfig.load(config_path=config_path)
        logger.info(f"[VIBE] Loaded configuration: active_model={_vibe_config.active_model}")
    return _vibe_config


def sync_vibe_configuration() -> None:
    """Sync active vibe_config.toml and support files to VIBE_HOME."""
    try:
        # Load config to resolve paths
        config = get_vibe_config()

        # Determine VIBE_HOME from config or env
        vibe_home = (
            Path(config.vibe_home)
            if config.vibe_home
            else Path(os.getenv("VIBE_HOME", str(Path.home() / ".vibe")))
        )
        vibe_home_config = vibe_home / "config.toml"

        # Determine Source Config Root (where templates are synced)
        source_root = DEFAULT_CONFIG_ROOT
        source_config_path = (
            Path(VIBE_CONFIG_FILE) if VIBE_CONFIG_FILE else source_root / "vibe_config.toml"
        )

        if not source_config_path.exists():
            logger.warning(f"Source config not found at {source_config_path}, skipping sync")
            return

        # Ensure VIBE_HOME structure exists
        vibe_home.mkdir(parents=True, exist_ok=True)
        (vibe_home / "prompts").mkdir(exist_ok=True)
        (vibe_home / "agents").mkdir(exist_ok=True)

        # 1. Sync main config.toml
        # Always sync if source is newer or target missing
        should_sync_main = not vibe_home_config.exists()
        if not should_sync_main:
            try:
                if source_config_path.stat().st_mtime > vibe_home_config.stat().st_mtime:
                    should_sync_main = True
            except OSError:
                should_sync_main = True

        if should_sync_main:
            shutil.copy2(source_config_path, vibe_home_config)
            logger.info(f"Synced Vibe config to: {vibe_home_config}")

        # 2. Sync agents and prompts folders from source_root/vibe/
        # These are usually populated by sync_config_templates.js
        for folder_name in ["agents", "prompts"]:
            src_folder = source_root / "vibe" / folder_name
            dst_folder = vibe_home / folder_name

            if src_folder.exists() and src_folder.is_dir():
                for src_file in src_folder.glob("*.toml"):
                    dst_file = dst_folder / src_file.name

                    # If it's a symlink in VIBE_HOME, we might want to respect it,
                    # but usually we want actual files for Vibe's portability
                    if not dst_file.exists() or src_file.stat().st_mtime > dst_file.stat().st_mtime:
                        if dst_file.is_symlink():
                            dst_file.unlink()
                        shutil.copy2(src_file, dst_file)
                        logger.debug(f"Synced Vibe {folder_name}: {src_file.name}")

    except Exception as e:
        logger.error(f"Failed to sync Vibe configuration: {e}")


def reload_vibe_config() -> VibeConfig:
    """Force reload the Vibe configuration."""
    global _vibe_config
    _vibe_config = None
    return get_vibe_config()


# =============================================================================
# INITIALIZATION
# =============================================================================

server = FastMCP("vibe")

logger.info(
    f"[VIBE] Server initialized | "
    f"Binary: {VIBE_BINARY} | "
    f"Workspace: {VIBE_WORKSPACE} | "
    f"Timeout: {DEFAULT_TIMEOUT_S}s",
)

# Perform startup sync
sync_vibe_configuration()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    if not isinstance(text, str):
        return str(text)
    return ANSI_ESCAPE.sub("", text)


async def is_network_available(
    host: str = "api.mistral.ai",
    port: int = 443,
    timeout: float = 3.0,
) -> bool:
    """Check if the network and specific host are reachable."""
    try:
        await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        return True
    except (TimeoutError, OSError) as e:
        logger.warning(f"[VIBE] Network check failed for {host}:{port}: {e}")
        return False


def truncate_output(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """Truncate text with indicator if exceeded."""
    if not isinstance(text, str):
        text = str(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n...[TRUNCATED: Output exceeded {max_chars} chars]..."


def resolve_vibe_binary() -> str | None:
    """Resolve the path to the Vibe CLI binary."""
    # Try ~/.local/bin first (common location)
    local_bin = os.path.expanduser("~/.local/bin/vibe")
    if os.path.exists(local_bin):
        return local_bin

    # Try absolute path from config
    if os.path.isabs(VIBE_BINARY) and os.path.exists(VIBE_BINARY):
        return VIBE_BINARY

    # Search PATH
    found = shutil.which(VIBE_BINARY)
    if found:
        return found

    logger.warning(f"Vibe binary '{VIBE_BINARY}' not found")
    return None


def prepare_workspace_and_instructions() -> None:
    """Ensure necessary directories exist."""
    try:
        Path(VIBE_WORKSPACE).mkdir(parents=True, exist_ok=True)
        Path(INSTRUCTIONS_DIR).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Workspace ready: {VIBE_WORKSPACE}")
    except Exception as e:
        logger.error(f"Failed to create workspace: {e}")


def cleanup_old_instructions(max_age_hours: int = 24) -> int:
    """Remove instruction files older than max_age_hours."""
    instructions_path = Path(INSTRUCTIONS_DIR)
    if not instructions_path.exists():
        return 0

    now = datetime.now()
    cleaned = 0
    try:
        for f in instructions_path.glob("vibe_instructions_*.md"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if (now - mtime).total_seconds() > max_age_hours * 3600:
                    f.unlink()
                    cleaned += 1
            except Exception as e:
                logger.debug(f"Failed to cleanup {f.name}: {e}")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

    if cleaned > 0:
        logger.info(f"Cleaned {cleaned} old instruction files")
    return cleaned


def handle_long_prompt(prompt: str, cwd: str | None = None) -> tuple[str, str | None]:
    """Handle long prompts by offloading to a file.
    Returns (final_prompt_arg, file_path_to_cleanup)
    """
    if len(prompt) <= 2000:
        return prompt, None

    try:
        os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)

        timestamp = int(datetime.now().timestamp())
        unique_id = uuid.uuid4().hex[:6]
        filename = f"vibe_instructions_{timestamp}_{unique_id}.md"
        filepath = os.path.join(INSTRUCTIONS_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("# VIBE INSTRUCTIONS\n\n")
            f.write(prompt)

        logger.debug(f"Large prompt ({len(prompt)} chars) stored at {filepath}")

        # Return a reference to the file
        return f"Read and execute the instructions from file: {filepath}", filepath

    except Exception as e:
        logger.warning(f"Failed to offload prompt: {e}")
        # Fallback: truncate if necessary
        if len(prompt) > 10000:
            return prompt[:10000] + "\n[TRUNCATED]", None
        return prompt, None


def _generate_task_session_id(prompt: str) -> str:
    """Generate a stable session ID from prompt content to enable context reuse."""
    import hashlib

    # We hash the first 500 chars of the prompt to create a 'task key'
    # This ensures that related calls for the same task use the same session
    clean_prompt = prompt.strip()[:500]
    h = hashlib.sha256(clean_prompt.encode()).hexdigest()
    return f"task-{h[:12]}"


async def run_vibe_subprocess(
    argv: list[str],
    cwd: str | None,
    timeout_s: float,
    env: dict[str, str] | None = None,
    ctx: Context | None = None,
    prompt_preview: str | None = None,
) -> dict[str, Any]:
    """Execute Vibe CLI subprocess with streaming output and global queueing."""
    global VIBE_QUEUE_SIZE
    process_env = _prepare_vibe_env(env)

    # Queue Management
    VIBE_QUEUE_SIZE += 1
    if VIBE_LOCK.locked():
        msg = f"⏳ [VIBE-QUEUE] Task queued (Position: {VIBE_QUEUE_SIZE - 1}). Waiting for active task to complete..."
        logger.info(msg)
        await _emit_vibe_log(ctx, "info", msg)

    async with VIBE_LOCK:
        VIBE_QUEUE_SIZE -= 1
        logger.debug(f"[VIBE] Executing: {' '.join(argv)}")

        if prompt_preview:
            await _emit_vibe_log(
                ctx, "info", f"🚀 [VIBE-LIVE] Запуск Vibe: {prompt_preview[:80]}..."
            )

        try:
            return await _execute_vibe_with_retries(argv, cwd, timeout_s, process_env, ctx)
        except Exception as outer_e:
            error_msg = f"Outer subprocess error: {outer_e}"
            logger.error(f"[VIBE] {error_msg}")
            return {"success": False, "error": error_msg, "command": argv}


def _prepare_vibe_env(env: dict[str, str] | None) -> dict[str, str]:
    """Prepare environment variables for Vibe subprocess."""
    config = get_vibe_config()
    process_env = os.environ.copy()
    process_env.update(config.get_environment())
    if env:
        process_env.update({k: str(v) for k, v in env.items()})
    return process_env


async def _emit_vibe_log(ctx: Context | None, level: str, message: str) -> None:
    """Emit log message to the client context."""
    if not ctx:
        return
    try:
        # Cast level string to Literal expected by ctx.log
        log_level = cast(Literal["debug", "info", "warning", "error"], level)
        await ctx.log(log_level, message, logger_name="vibe_mcp")
    except Exception as e:
        logger.debug(f"[VIBE] Failed to send log to client: {e}")


async def _handle_vibe_line(line: str, stream_name: str, ctx: Context | None) -> None:
    """Process and log a single line of output from Vibe."""
    line = _clean_vibe_line(line)
    if not line:
        return

    # Try structured logging first
    if await _try_parse_structured_vibe_log(line, ctx):
        return

    # Fallback to standard streaming log
    await _format_and_emit_vibe_log(line, stream_name, ctx)


def _clean_vibe_line(line: str) -> str:
    """Filter out terminal control characters and TUI artifacts."""
    if not line:
        return ""
    if any(c < "\x20" for c in line if c not in "\t\n\r"):
        line = "".join(c for c in line if c >= "\x20" or c in "\t\n\r")
    return line.strip()


async def _try_parse_structured_vibe_log(line: str, ctx: Context | None) -> bool:
    """Try to parse as JSON for structured logging."""
    try:
        obj = json.loads(line)
        if not isinstance(obj, dict) or not obj.get("role") or not obj.get("content"):
            return False

        role_map = {
            "assistant": "🧠 [VIBE-THOUGHT]",
            "tool": "🔧 [VIBE-ACTION]",
        }
        prefix = role_map.get(obj["role"], "💬 [VIBE-GEN]")
        message = f"{prefix} {str(obj['content'])[:200]}"

        logger.info(message)
        await _emit_vibe_log(ctx, "info", message)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


async def _format_and_emit_vibe_log(line: str, stream_name: str, ctx: Context | None) -> None:
    """Format and emit a standard log line."""
    if any(t in line for t in SPAM_TRIGGERS):
        return

    if len(line) >= 1000:
        return

    if "Thinking" in line or "Planning" in line:
        formatted = f"🧠 [VIBE-THOUGHT] {line}"
    elif "Running" in line or "Executing" in line:
        formatted = f"🔧 [VIBE-ACTION] {line}"
    else:
        formatted = f"⚡ [VIBE-LIVE] {line}"

    logger.debug(f"[VIBE_{stream_name}] {line}")
    level = "warning" if stream_name == "ERR" else "info"
    await _emit_vibe_log(ctx, level, formatted)


async def _read_vibe_stream(
    stream: asyncio.StreamReader,
    chunks: list[bytes],
    stream_name: str,
    timeout_s: float,
    ctx: Context | None,
) -> None:
    """Read from Vibe stream and process lines."""
    buffer = b""
    try:
        while True:
            data = await stream.read(8192)
            if not data:
                break
            chunks.append(data)
            buffer += data
            while b"\n" in buffer:
                line_bytes, buffer = buffer.split(b"\n", 1)
                line = strip_ansi(line_bytes.decode(errors="replace")).strip()
                await _handle_vibe_line(line, stream_name, ctx)
        if buffer:
            line = strip_ansi(buffer.decode(errors="replace")).strip()
            await _handle_vibe_line(line, stream_name, ctx)
    except TimeoutError:
        logger.warning(f"[VIBE] Read timeout on {stream_name} after {timeout_s}s")
    except Exception as e:
        logger.error(f"[VIBE] Stream reading error ({stream_name}): {e}")


async def _execute_vibe_with_retries(
    argv: list[str],
    cwd: str | None,
    timeout_s: float,
    process_env: dict[str, str],
    ctx: Context | None,
) -> dict[str, Any]:
    """Execute loop with retries for Vibe subprocess."""
    MAX_RETRIES = 5
    # Increased backoff delays to better handle Mistral rate limits
    BACKOFF_DELAYS = [60, 120, 240, 480, 600]

    for attempt in range(MAX_RETRIES):
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=cwd or VIBE_WORKSPACE,
                env=process_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )

            stdout_chunks: list[bytes] = []
            stderr_chunks: list[bytes] = []

            tasks: list[Any] = []
            if process.stdout:
                tasks.append(
                    _read_vibe_stream(process.stdout, stdout_chunks, "OUT", timeout_s, ctx)
                )
            if process.stderr:
                tasks.append(
                    _read_vibe_stream(process.stderr, stderr_chunks, "ERR", timeout_s, ctx)
                )
            tasks.append(process.wait())

            try:
                # Cast to Any to avoid strict Awaitable[tuple] vs Awaitable[list] mismatch in some Pyrefly versions
                gather_fut = cast(Any, asyncio.gather(*tasks))
                await asyncio.wait_for(gather_fut, timeout=timeout_s + 20)
                await _emit_vibe_log(ctx, "info", "✅ [VIBE-LIVE] Vibe завершив роботу успішно")
            except TimeoutError:
                return await _handle_vibe_timeout(
                    process, argv, timeout_s, stdout_chunks, stderr_chunks, ctx
                )

            stdout = strip_ansi(b"".join(stdout_chunks).decode(errors="replace"))
            stderr = strip_ansi(b"".join(stderr_chunks).decode(errors="replace"))

            # Check for API rate limits
            if "Rate limit exceeded" in stderr or "Rate limit exceeded" in stdout:
                res = await _handle_vibe_rate_limit(
                    attempt, MAX_RETRIES, BACKOFF_DELAYS, stdout, stderr, argv, ctx
                )
                if isinstance(res, bool) and res is True:  # Continue to next retry
                    continue
                return cast(dict[str, Any], res)

            # Check for Session not found (failed resume)
            # Use regex for more robust detection of Vibe session errors (Iteration 3)
            session_patterns = [
                r"session '.*' not found",
                r"not found in .*logs/session",
                r"failed to resume session",
            ]

            session_error = any(
                re.search(p, stderr, re.IGNORECASE | re.DOTALL)
                or re.search(p, stdout, re.IGNORECASE | re.DOTALL)
                for p in session_patterns
            )

            if session_error and "--resume" in argv:
                logger.warning(
                    f"[VIBE-RETRY-DIAG] Session error detected. Retrying without --resume. ID: {uuid.uuid4().hex[:8]}"
                )
                try:
                    idx = argv.index("--resume")
                    argv.pop(idx)  # remove --resume
                    if idx < len(argv):
                        argv.pop(idx)  # remove session_id
                    # Continue loop to retry immediately with updated argv
                    continue
                except (ValueError, IndexError):
                    pass

            if process.returncode != 0:
                logger.debug(
                    f"[VIBE-FAIL-DIAG] Code {process.returncode}. Out length: {len(stdout)}. Err length: {len(stderr)}"
                )
                logger.debug(f"[VIBE-FAIL-SNIPPET] Stderr snippet: {stderr[-500:]}")

            return {
                "success": process.returncode == 0,
                "returncode": process.returncode,
                "stdout": truncate_output(stdout),
                "stderr": truncate_output(stderr),
                "command": argv,
            }
        except FileNotFoundError:
            return {"success": False, "error": f"Vibe binary not found: {argv[0]}", "command": argv}
        except Exception as e:
            logger.error(f"[VIBE] Subprocess error during attempt {attempt + 1}: {e}")
            if attempt == MAX_RETRIES - 1:
                return {"success": False, "error": str(e), "command": argv}

    return {"success": False, "error": "Retries exhausted", "command": argv}


async def _handle_vibe_timeout(
    process: asyncio.subprocess.Process,
    argv: list[str],
    timeout_s: float,
    stdout_chunks: list[bytes],
    stderr_chunks: list[bytes],
    ctx: Context | None,
) -> dict[str, Any]:
    """Handle process timeout by terminating/killing and returning partial output."""
    logger.warning(f"[VIBE] Process timeout ({timeout_s}s), terminating")
    await _emit_vibe_log(ctx, "warning", f"⏱️ [VIBE-LIVE] Перевищено timeout ({timeout_s}s)")

    try:
        process.terminate()
        await asyncio.wait_for(process.wait(), timeout=5)
    except TimeoutError:
        process.kill()
        await process.wait()

    stdout_str = strip_ansi(b"".join(stdout_chunks).decode(errors="replace"))
    stderr_str = strip_ansi(b"".join(stderr_chunks).decode(errors="replace"))

    return {
        "success": False,
        "error": f"Vibe execution timed out after {timeout_s}s",
        "returncode": -1,
        "stdout": truncate_output(stdout_str),
        "stderr": truncate_output(stderr_str),
        "command": argv,
    }


async def _handle_vibe_rate_limit(
    attempt: int,
    max_retries: int,
    backoff_delays: list[int],
    stdout: str,
    stderr: str,
    argv: list[str],
    ctx: Context | None,
) -> bool | dict[str, Any]:
    """Handle rate limit errors with backoff or report failure."""
    global _current_model

    if attempt < max_retries - 1:
        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0, 15)
        wait_time = backoff_delays[attempt] + jitter
        logger.warning(
            f"[VIBE] Rate limit detected (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time:.1f}s..."
        )
        await _emit_vibe_log(
            ctx,
            "warning",
            f"⚠️ [VIBE-RATE-LIMIT] Перевищено ліміт запитів Mistral API. Спроба {attempt + 1}/{max_retries}. Очікування {wait_time:.0f}с...",
        )
        await asyncio.sleep(wait_time)
        return True

    # Try OpenRouter fallback before giving up
    config = get_vibe_config()
    openrouter_model = config.get_model_by_alias("devstral-openrouter")
    if openrouter_model and _current_model != "devstral-openrouter":
        provider = config.get_provider("openrouter")
        if provider and provider.is_available():
            logger.info("[VIBE] Mistral rate limit exhausted. Switching to OpenRouter fallback...")
            await _emit_vibe_log(
                ctx,
                "info",
                "🔄 [VIBE-FALLBACK] Переключаюсь на OpenRouter (безкоштовний devstral)...",
            )
            _current_model = "devstral-openrouter"
            # Update argv to use the new model for retry
            # Find and update --model argument, or append if not present
            model_found = False
            for i, arg in enumerate(argv):
                if arg == "--model" and i + 1 < len(argv):
                    argv[i + 1] = "devstral-openrouter"
                    model_found = True
                    break
            if not model_found:
                # Insert --model after the vibe binary path
                argv.insert(1, "--model")
                argv.insert(2, "devstral-openrouter")
            logger.debug(f"[VIBE] Updated argv for OpenRouter: {' '.join(argv[:5])}...")
            return True  # Signal retry with new model

    error_msg = (
        f"Mistral API rate limit exceeded after {max_retries} attempts. "
        f"Please wait a few minutes or check API quota."
    )
    logger.error(f"[VIBE] {error_msg}")
    await _emit_vibe_log(ctx, "error", f"❌ [VIBE-RATE-LIMIT] {error_msg}")
    return {
        "success": False,
        "error": error_msg,
        "error_type": "RATE_LIMIT",
        "returncode": 1,
        "stdout": truncate_output(stdout),
        "stderr": truncate_output(stderr),
        "command": argv,
    }


@server.tool()
async def vibe_test_in_sandbox(
    ctx: Context,
    test_script: str,
    target_files: dict[str, str],
    command: str,
    dependencies: list[str] | None = None,
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    """Execute a test script in an isolated temporary sandbox.

    Args:
        test_script: Content of the test script (e.g., Python unit test)
        target_files: Dictionary of {filename: content} to mock/create in sandbox
        command: Command to run (e.g., "python test_script.py")
        dependencies: (Optional) Mock dependencies or instructions
        timeout_s: Execution timeout (default: 30s)

    Returns:
        Execution results (stdout, stderr, returncode)
    """
    logger.info(f"[VIBE] Sandbox execution requested: {command}")

    # Create temp directory
    try:
        with tempfile.TemporaryDirectory(prefix="vibe_sandbox_") as sandbox_dir:
            # 1. Write target files
            for fname, content in target_files.items():
                fpath = os.path.join(sandbox_dir, fname)
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(content)

            # 2. Write test script to checking file
            # If command references a specific file, stick to it, otherwise default
            runner_main = "vibe_test_runner.py"
            runner_path = os.path.join(sandbox_dir, runner_main)
            with open(runner_path, "w", encoding="utf-8") as f:
                f.write(test_script)

            # 3. Execute
            logger.debug(f"Running sandbox command in {sandbox_dir}")

            # Prepare env
            env = os.environ.copy()
            env["PYTHONPATH"] = sandbox_dir  # Add sandbox to path

            process = await asyncio.create_subprocess_shell(
                command,
                cwd=sandbox_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_s)

            return {
                "success": process.returncode == 0,
                "returncode": process.returncode,
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
                "sandbox_dir_was": sandbox_dir,
            }

    except TimeoutError:
        return {
            "success": False,
            "error": f"Sandbox execution timed out after {timeout_s}s",
            "returncode": -1,
        }
    except Exception as e:
        return {"success": False, "error": f"Sandbox internal error: {e}", "returncode": -1}


# =============================================================================
# MCP TOOLS - CORE (6 tools)
# =============================================================================


@server.tool()
async def vibe_which(ctx: Context) -> dict[str, Any]:
    """Locate the Vibe CLI binary and report its version and configuration.

    Returns:
        Dict with 'binary' path, 'version', current 'model', and 'mode'

    """
    vibe_path = resolve_vibe_binary()
    if not vibe_path:
        logger.warning("[VIBE] Binary not found on PATH")
        return {
            "success": False,
            "error": f"Vibe CLI not found (binary='{VIBE_BINARY}')",
        }

    logger.debug(f"[VIBE] Found binary at: {vibe_path}")

    try:
        process = await asyncio.create_subprocess_exec(
            vibe_path,
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await asyncio.wait_for(process.communicate(), timeout=10)
        version = stdout.decode().strip() if process.returncode == 0 else "unknown"
    except Exception as e:
        logger.warning(f"Failed to get Vibe version: {e}")
        version = "unknown"

    config = get_vibe_config()

    return {
        "success": True,
        "binary": vibe_path,
        "version": version,
        "active_model": _current_model or config.active_model,
        "mode": _current_mode.value,
        "available_models": [m.alias for m in config.get_available_models()],
    }


@server.tool()
async def vibe_prompt(
    ctx: Context,
    prompt: str,
    cwd: str | None = None,
    timeout_s: float | None = None,
    # Enhanced options
    model: str | None = None,
    agent: str | None = None,
    mode: str | None = None,
    session_id: str | None = None,
    enabled_tools: list[str] | None = None,
    disabled_tools: list[str] | None = None,
    max_turns: int | None = None,
    max_price: float | None = None,
    output_format: str = "streaming",
) -> dict[str, Any]:
    """Send a prompt to Vibe AI agent in programmatic mode.

    The PRIMARY tool for interacting with Vibe. Executes in CLI mode with
    structured output. All execution is logged and visible.

    Args:
        prompt: The message/query for Vibe AI (Mistral-powered)
        cwd: Working directory for execution (default: vibe_workspace)
        timeout_s: Timeout in seconds (default from config)
        model: Model alias to use (overrides active_model)
        agent: Agent profile name (loads from agents directory)
        mode: Operational mode (plan/auto-approve/accept-edits)
        session_id: Session ID to resume
        enabled_tools: Additional tools to enable (glob/regex patterns)
        disabled_tools: Additional tools to disable (glob/regex patterns)
        max_turns: Maximum conversation turns
        max_price: Maximum cost limit in dollars
        output_format: Output format (streaming/json/text)

    Returns:
        Dict with 'success', 'stdout', 'stderr', 'returncode', 'parsed_response'

    """
    prepare_workspace_and_instructions()

    vibe_path = resolve_vibe_binary()
    if not vibe_path:
        return {
            "success": False,
            "error": "Vibe CLI not found on PATH",
        }

    config = get_vibe_config()
    eff_timeout = timeout_s if timeout_s is not None else config.timeout_s
    # Default to PROJECT_ROOT for project operations, fall back to workspace
    eff_cwd = cwd or str(PROJECT_ROOT)
    if not os.path.exists(eff_cwd):
        eff_cwd = VIBE_WORKSPACE

    # Ensure workspace exists (for instructions/logs)
    os.makedirs(VIBE_WORKSPACE, exist_ok=True)
    if eff_cwd != VIBE_WORKSPACE:
        os.makedirs(eff_cwd, exist_ok=True)

    # Check network before proceeding if it's an AI prompt
    if not await is_network_available():
        return {
            "success": False,
            "error": "Mistral API is unreachable. Please check your internet connection.",
            "returncode": -2,
        }

    # Validate output_format to avoid CLI errors (only text, json, streaming supported)
    valid_formats = {"text", "json", "streaming"}
    if output_format not in valid_formats:
        logger.warning(
            f"[VIBE] Invalid output_format '{output_format}' requested. "
            f"Falling back to 'streaming'. valid_formats={valid_formats}"
        )
        output_format = "streaming"

    final_prompt, prompt_file_to_clean = handle_long_prompt(prompt, eff_cwd)

    # Automatic Session Persistence (if not provided)
    eff_session_id = session_id or _generate_task_session_id(prompt)

    try:
        # Determine effective mode
        effective_mode = AgentMode(mode) if mode else _current_mode

        # Build command using config
        argv = [
            vibe_path,
            *config.to_cli_args(
                prompt=final_prompt,
                cwd=eff_cwd,
                mode=effective_mode,
                model=model or _current_model,
                agent=agent,
                session_id=eff_session_id,
                max_turns=max_turns,
                max_price=max_price,
                output_format=output_format,
            ),
        ]

        logger.info(f"[VIBE] Executing prompt: {prompt[:50]}... (timeout={eff_timeout}s)")

        result = await run_vibe_subprocess(
            argv=argv,
            cwd=eff_cwd,
            timeout_s=eff_timeout,
            ctx=ctx,
            prompt_preview=prompt,
        )

        # Try to parse JSON response
        if result.get("success") and result.get("stdout"):
            try:
                result["parsed_response"] = json.loads(result["stdout"])
            except json.JSONDecodeError:
                # Try to extract JSON from streaming format
                lines = result["stdout"].split("\n")
                json_lines = [line for line in lines if line.strip().startswith("{")]
                if json_lines:
                    try:
                        result["parsed_response"] = json.loads(json_lines[-1])
                    except json.JSONDecodeError:
                        result["parsed_response"] = None

        return result

    finally:
        # Cleanup temporary file
        if prompt_file_to_clean and os.path.exists(prompt_file_to_clean):
            try:
                os.remove(prompt_file_to_clean)
                logger.debug(f"Cleaned up prompt file: {prompt_file_to_clean}")
            except Exception as e:
                logger.warning(f"Failed to cleanup prompt file: {e}")


@server.tool()
async def vibe_analyze_error(
    ctx: Context,
    error_message: str,
    file_path: str | None = None,
    log_context: str | None = None,
    recovery_history: list[dict[str, Any]] | str | None = None,
    cwd: str | None = None,
    timeout_s: float | None = None,
    auto_fix: bool = True,
    session_id: str | None = None,
    # Enhanced context for better self-healing
    step_action: str | None = None,
    expected_result: str | None = None,
    actual_result: str | None = None,
    full_plan_context: str | None = None,
) -> dict[str, Any]:
    """Deep error analysis and optional auto-fix using Vibe AI.

    Designed for self-healing scenarios when the system encounters errors
    it cannot resolve. Vibe acts as a Senior Engineer.

    Args:
        error_message: The error message or stack trace
        file_path: Path to the file with the error (if known)
        log_context: Recent log entries for context
        recovery_history: List of past recovery attempts or a summary string
        cwd: Working directory
        timeout_s: Timeout in seconds (default: 600)
        auto_fix: Automatically apply fixes (default: True)
        step_action: The action that was being performed when the error occurred
        expected_result: What was expected to happen
        actual_result: What actually happened
        full_plan_context: The full execution plan for context

    Returns:
        Analysis with root cause, suggested or applied fixes, and verification

    """
    prepare_workspace_and_instructions()

    # Build structured problem report
    prompt_parts = [
        "=" * 60,
        "ATLASTRINITY SELF-HEALING DIAGNOSTIC REPORT",
        "=",
        "ROLE: Senior Architect & Self-Healing Engineer.",
        "MISSION: Diagnose with ARCHITECTURAL AWARENESS, fix, and verify.",
        "",
        "CONTEXT NOTE: Architecture diagrams have been refreshed and are available",
        "in `src/brain/data/architecture_diagrams/mcp_architecture.md`.",
        "Please use them to understand component interactions.",
        "",
        "=",
        "1. WHAT HAPPENED (Problem Description)",
        "=" * 40,
        f"ERROR MESSAGE:\n{error_message}",
    ]

    # Add step context if available
    if step_action:
        prompt_parts.extend(
            [
                "",
                f"STEP ACTION: {step_action}",
            ],
        )

    if expected_result:
        prompt_parts.append(f"EXPECTED RESULT: {expected_result}")

    if actual_result:
        prompt_parts.append(f"ACTUAL RESULT: {actual_result}")

    prompt_parts.extend(
        [
            "",
            "=" * 40,
            "2. CONTEXT (Environment & History)",
            "=" * 40,
            f"System Root: {SYSTEM_ROOT}",
            f"Project Directory: {cwd or VIBE_WORKSPACE}",
            "",
            "DATABASE SCHEMA (for reference):",
            "- sessions: id, started_at, ended_at",
            "- tasks: id, session_id, goal, status, created_at",
            "- task_steps: id, task_id, sequence_number, action, tool, status, error_message",
            "- tool_executions: id, step_id, server_name, tool_name, arguments, result",
        ],
    )

    if log_context:
        prompt_parts.extend(
            [
                "",
                "RECENT LOGS:",
                log_context,
            ],
        )

    if recovery_history:
        prompt_parts.extend(
            [
                "",
                "=" * 40,
                "3. PAST ATTEMPTS (What Was Already Tried)",
                "=" * 40,
            ],
        )
        if isinstance(recovery_history, list):
            for i, attempt in enumerate(recovery_history):
                status = "✅ SUCCESS" if attempt.get("status") == "success" else "❌ FAILED"
                prompt_parts.append(
                    f"Attempt {i + 1}: {attempt.get('action', 'Unknown')} | {status}",
                )
                if attempt.get("error"):
                    prompt_parts.append(f"  └─ Error: {attempt.get('error')}")
            prompt_parts.append("")
            prompt_parts.append("⚠️ CRITICAL: Do NOT repeat strategies that have already failed!")
        else:
            prompt_parts.append(recovery_history)
            prompt_parts.append("⚠️ CRITICAL: Do NOT repeat strategies that have already failed!")

    if full_plan_context:
        prompt_parts.extend(
            [
                "",
                "FULL PLAN CONTEXT:",
                str(full_plan_context)[:1000],  # More aggressive limit
            ],
        )

    if log_context:
        # Instead of embedding logs, we tell Vibe where to find them and give a tiny snippet
        prompt_parts.extend(
            [
                "",
                "2.1 RECENT LOGS (Pointer-based Context)",
                "=" * 40,
                f"Full log file: {DEFAULT_CONFIG_ROOT}/logs/vibe_server.log",
                "ACTION: Use your 'read_file' or 'filesystem_read' tool to inspect this file.",
                "",
                "BRIEF LOG SNIPPET (for quick orientation):",
                str(log_context)[-2000:],  # Only last 2k for orientation
            ],
        )

    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                # If file is huge, take just the relevant part if we can guess line number
                # For now, just take a smaller chunk to be safe
                prompt_parts.extend(
                    [
                        "",
                        f"RELEVANT FILE: {file_path}",
                        "```",
                        content[:3000],
                        "```",
                    ],
                )
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")

    prompt_parts.extend(
        [
            "",
            "=" * 40,
            "4. YOUR INSTRUCTIONS",
            "=" * 40,
        ],
    )

    if auto_fix:
        prompt_parts.extend(
            [
                "",
                "PHASE 1 - DIAGNOSE:",
                "  1.1. Perform Root Cause Analysis (RCA) - identify the EXACT cause",
                "  1.2. Explain WHY this error occurred (not just what happened)",
                "  1.3. Check if this is related to configuration, codebase, or environment limits (macOS vs iOS)",
                f"  1.4. Apply guidelines from: {MACOS_DEVELOPMENT_GUIDELINES}",
                "",
                "PHASE 2 - FIX:",
                "  2.1. Create a fix strategy with clear rationale",
                "  2.2. Execute the fix (edit code, run commands as needed)",
                "  2.3. Ensure the fix addresses the ROOT CAUSE, not symptoms",
                f"  2.4. Follow DYNAMIC VERIFICATION: {DYNAMIC_VERIFICATION_PROTOCOL}",
                "",
                "PHASE 2.5 - SANDBOX VERIFICATION (CRITICAL):",
                "  2.5.1. Before applying any fix to the main codebase, TRY to reproduce the fix in a sandbox.",
                "  2.5.2. Use the 'vibe_test_in_sandbox' tool if available.",
                "  2.5.3. Create a minimal reproduction script and verify your fix actually works.",
                "  2.5.4. If sandbox test passes, ONLY THEN apply the fix to the main codebase.",
                "",
                "PHASE 3 - VERIFY:",
                "  3.1. Verify the fix works by running appropriate checks",
                "  3.2. Confirm no new issues were introduced",
                "  3.3. Report results with evidence of success",
                "",
                "PHASE 4 - PREVENTION:",
                "  4.1. Identify if this issue was caused by a systemic weakness (invalid path logic, missing config, unstable utility).",
                "  4.2. PROPOSE and (if safe) APPLY a preventative measure: update configuration templates, improve utility functions, or add more robust error handling in the culprit module.",
                "  4.3. Ensure that 'fixing for yourself' means the system is now more resilient to this specific class of errors.",
                "",
                "OUTPUT FORMAT:",
                "Provide a structured response with:",
                "- ROOT_CAUSE: [description]",
                "- FIX_APPLIED: [what was changed now]",
                "- PREVENTION_MEASURE: [what was changed to prevent recurrence]",
                "- VERIFICATION: [evidence of success]",
                "- voice_message: [Direct speech to the user in Ukrainian, explaining what you did]",
                "- STATUS: SUCCESS | PARTIAL | FAILED",
            ],
        )
    else:
        prompt_parts.extend(
            [
                "",
                "ANALYSIS MODE (no changes):",
                "1. Perform deep root cause analysis",
                "2. Explain WHY this error occurred",
                "3. Suggest specific fixes with rationale",
                "4. Estimate complexity and risk of each fix",
                "",
                "Do NOT apply any changes - analysis only.",
            ],
        )

    prompt = "\n".join(prompt_parts)

    logger.info(f"[VIBE] Analyzing error (auto_fix={auto_fix}, step={step_action})")

    return cast(
        dict[str, Any],
        await vibe_prompt(
            ctx=ctx,
            prompt=prompt,
            cwd=cwd,
            timeout_s=timeout_s or DEFAULT_TIMEOUT_S,
            model=AGENT_MODEL_OVERRIDE,
            mode="auto-approve" if auto_fix else "plan",
            session_id=session_id,
            max_turns=config.max_turns,
        ),
    )


@server.tool()
async def vibe_implement_feature(
    ctx: Context,
    goal: str,
    context_files: list[str] | None = None,
    constraints: str | None = None,
    cwd: str | None = None,
    timeout_s: float | None = 1200,
    session_id: str | None = None,
    # Enhanced options for software development
    quality_checks: bool = True,
    iterative_review: bool = True,
    max_iterations: int = 3,
    run_linting: bool = True,
    code_style: str = "ruff",
) -> dict[str, Any]:
    """Deep coding mode: Implements a complex feature or refactoring.

    Vibe acts as a Senior Architect to plan, implement, verify, and iteratively
    improve the code until quality standards are met.

    Args:
        goal: High-level objective (e.g., "Add user profile page with API and DB")
        context_files: List of relevant file paths
        constraints: Technical constraints or guidelines
        cwd: Working directory
        timeout_s: Timeout (default: 1200s for deep work)
        quality_checks: Run lint/syntax checks after implementation (default: True)
        iterative_review: Self-review and fix issues until clean (default: True)
        max_iterations: Maximum review/fix iterations (default: 3)
        run_linting: Run linter on modified files (default: True)
        code_style: Linter to use - "ruff" or "pylint" (default: "ruff")

    Returns:
        Implementation report with changed files, verification results, and quality metrics

    """
    prepare_workspace_and_instructions()

    # Gather file contents
    file_contents = []
    if context_files:
        for fpath in context_files:
            if os.path.exists(fpath):
                try:
                    with open(fpath, encoding="utf-8") as f:
                        content = f.read()[:3000]  # Reduced limit for token efficiency
                        file_contents.append(f"FILE: {fpath}\n```\n{content}\n```")
                except Exception as e:
                    file_contents.append(f"FILE: {fpath} (Error: {e})")
            else:
                file_contents.append(f"FILE: {fpath} (Not found, will create)")

    context_str = "\n\n".join(file_contents) if file_contents else "(No files provided)"

    # Build enhanced prompt with iterative workflow
    quality_section = ""
    if quality_checks:
        quality_section = f"""
QUALITY REQUIREMENTS:
- All code must pass {code_style} linting
- Type hints required for function parameters and returns
- Docstrings required for public functions
- Error handling for external operations
- No hardcoded secrets or credentials
"""

    iterative_section = ""
    if iterative_review:
        iterative_section = f"""
ITERATIVE IMPROVEMENT PROTOCOL:
After initial implementation, follow this loop (max {max_iterations} iterations):

1. RUN DYNAMIC VERIFICATION:
   - {DYNAMIC_VERIFICATION_PROTOCOL}
   - IF APPLICABLE: Use 'vibe_test_in_sandbox' to verify isolated logic before integration.
   
2. SELF-REVIEW:
   - Verify compliance with: {MACOS_DEVELOPMENT_GUIDELINES}
   - Check for edge cases not handled
   - Verify error messages are helpful
   - Ensure code is readable and maintainable
   
3. IF ISSUES FOUND:
   - Fix the issues
   - Return to step 1
   
4. IF CLEAN:
   - Report success with summary

Track your iterations and report final status.
"""

    prompt = f"""
============================================================
ATLASTRINITY SOFTWARE DEVELOPMENT TASK
============================================================

ROLE: You are the Senior Software Architect and Lead Developer for AtlasTrinity.
MISSION: Implement a feature that will work reliably in production.

GOAL:
{goal}

============================================================
CONTEXT FILES
============================================================
{context_str}

============================================================
CONSTRAINTS & GUIDELINES
============================================================
{constraints or "Standard project guidelines apply."}
{quality_section}

============================================================
ENVIRONMENT
============================================================
System Root: {SYSTEM_ROOT}
Project Directory: {cwd or VIBE_WORKSPACE}

============================================================
IMPLEMENTATION WORKFLOW
============================================================

PHASE 1 - ANALYZE & PLAN:
  1.1. Understand the goal completely
  1.2. Review existing code structure
  1.3. Identify files to create/modify
  1.4. Plan the implementation approach

PHASE 2 - IMPLEMENT:
  2.1. Create/edit necessary files
  2.2. Handle imports and dependencies
  2.3. Add proper error handling
  2.4. Include type hints and docstrings

PHASE 3 - VERIFY:
  3.1. Check syntax is valid
  3.2. Run linting checks
  3.3. Verify imports resolve correctly
{iterative_section}

PHASE 4 - REPORT:
  Provide a structured summary:
  - FILES_MODIFIED: [list of files]
  - FILES_CREATED: [list of files]
  - CHANGES_SUMMARY: [brief description]
  - VERIFICATION_STATUS: PASSED | FAILED
  - ISSUES_REMAINING: [any known issues]
  - NEXT_STEPS: [recommendations if any]

============================================================
EXECUTE NOW
============================================================
"""

    logger.info(f"[VIBE] Implementing feature: {goal[:50]}... (iterative={iterative_review})")

    return cast(
        dict[str, Any],
        await vibe_prompt(
            ctx=ctx,
            prompt=prompt,
            cwd=cwd,
            timeout_s=timeout_s or 1200,
            model=AGENT_MODEL_OVERRIDE,
            mode="auto-approve",
            session_id=session_id,
            max_turns=30 + (max_iterations * 5 if iterative_review else 0),
        ),
    )


@server.tool()
async def vibe_code_review(
    ctx: Context,
    file_path: str,
    focus_areas: str | None = None,
    cwd: str | None = None,
    timeout_s: float | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Request a code review from Vibe AI for a specific file.

    Args:
        file_path: Path to the file to review
        focus_areas: Specific areas to focus on (e.g., "security", "performance")
        cwd: Working directory
        timeout_s: Timeout in seconds (default: 300)

    Returns:
        Code review analysis with suggestions

    """
    if not os.path.exists(file_path):
        return {
            "success": False,
            "error": f"File not found: {file_path}",
        }

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()[:10000]  # Limit
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not read file: {e}",
        }

    prompt_parts = [
        f"CODE REVIEW REQUEST: {file_path}",
        "",
        f"FILE CONTENT:\n```\n{content}\n```",
        "",
        "Please review this code and provide:",
        "1. Overall code quality assessment",
        "2. Potential bugs or issues",
        "3. Security concerns (if any)",
        "4. Performance improvements",
        "5. Code style and best practices",
    ]

    if focus_areas:
        prompt_parts.append(f"\nFOCUS AREAS: {focus_areas}")

    return cast(
        dict[str, Any],
        await vibe_prompt(
            ctx=ctx,
            prompt="\n".join(prompt_parts),
            cwd=cwd,
            timeout_s=timeout_s or 300,
            model=AGENT_MODEL_OVERRIDE,
            mode="plan",  # Read-only mode
            session_id=session_id,
            max_turns=5,
        ),
    )


@server.tool()
async def vibe_smart_plan(
    ctx: Context,
    objective: str,
    context: str | None = None,
    cwd: str | None = None,
    timeout_s: float | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Generate a smart execution plan for a complex objective.

    Args:
        objective: The goal or task to plan for
        context: Additional context (existing code, constraints, etc.)
        cwd: Working directory
        timeout_s: Timeout in seconds (default: 300)

    Returns:
        Structured plan with steps, actions, tools, and verification criteria

    """
    prompt_parts = [
        "CREATE A DETAILED EXECUTION PLAN",
        "",
        f"OBJECTIVE: {objective}",
    ]

    if context:
        prompt_parts.append(f"\nCONTEXT:\n{context}")

    prompt_parts.extend(
        [
            "",
            "For each step, specify:",
            "- Action to perform",
            "- Required tools/commands",
            "- Expected outcome",
            "- Verification criteria",
        ],
    )

    return cast(
        dict[str, Any],
        await vibe_prompt(
            ctx=ctx,
            prompt="\n".join(prompt_parts),
            cwd=cwd,
            timeout_s=timeout_s or 300,
            mode="plan",
            session_id=session_id,
            max_turns=5,
        ),
    )


# =============================================================================
# MCP TOOLS - CONFIGURATION (5 new tools)
# =============================================================================


@server.tool()
async def vibe_get_config(ctx: Context) -> dict[str, Any]:
    """Get the current Vibe configuration state.

    Returns:
        Current configuration including active model, mode, providers, and models

    """
    config = get_vibe_config()

    return {
        "success": True,
        "active_model": _current_model or config.active_model,
        "mode": _current_mode.value,
        "default_mode": config.default_mode.value,
        "max_turns": config.max_turns,
        "max_price": config.max_price,
        "timeout_s": config.timeout_s,
        "providers": [
            {
                "name": p.name,
                "api_base": p.api_base,
                "available": p.is_available(),
            }
            for p in config.providers
        ],
        "models": [
            {
                "alias": m.alias,
                "name": m.name,
                "provider": m.provider,
                "temperature": m.temperature,
            }
            for m in config.models
        ],
        "available_models": [m.alias for m in config.get_available_models()],
        "enabled_tools": config.enabled_tools,
        "disabled_tools": config.disabled_tools,
    }


@server.tool()
async def vibe_configure_model(
    ctx: Context,
    model_alias: str,
    persist: bool = False,
) -> dict[str, Any]:
    """Switch the active model for Vibe operations.

    Args:
        model_alias: Alias of the model to use (from models list)
        persist: If True, update the config file (not yet implemented)

    Returns:
        Confirmation with the new active model

    """
    global _current_model

    config = get_vibe_config()
    model = config.get_model_by_alias(model_alias)

    if not model:
        available = [m.alias for m in config.models]
        return {
            "success": False,
            "error": f"Model '{model_alias}' not found",
            "available_models": available,
        }

    # Check if provider is available
    provider = config.get_provider(model.provider)
    if not provider or not provider.is_available():
        return {
            "success": False,
            "error": f"Provider '{model.provider}' is not available (missing API key)",
            "hint": f"Set {provider.api_key_env_var if provider else 'API_KEY'} environment variable",
        }

    _current_model = model_alias
    logger.info(f"[VIBE] Switched active model to: {model_alias}")

    return {
        "success": True,
        "active_model": model_alias,
        "model_name": model.name,
        "provider": model.provider,
        "temperature": model.temperature,
    }


@server.tool()
async def vibe_set_mode(
    ctx: Context,
    mode: str,
) -> dict[str, Any]:
    """Change the operational mode for Vibe.

    Args:
        mode: Operational mode - "default", "plan", "accept-edits", or "auto-approve"
            - default: Requires confirmation for tool executions
            - plan: Read-only mode for exploration
            - accept-edits: Auto-approves file edit tools only
            - auto-approve: Auto-approves all tool executions

    Returns:
        Confirmation with the new mode

    """
    global _current_mode

    try:
        new_mode = AgentMode(mode)
    except ValueError:
        return {
            "success": False,
            "error": f"Invalid mode: '{mode}'",
            "valid_modes": [m.value for m in AgentMode],
        }

    _current_mode = new_mode
    logger.info(f"[VIBE] Changed operational mode to: {mode}")

    return {
        "success": True,
        "mode": mode,
        "description": {
            "default": "Requires confirmation for tool executions",
            "plan": "Read-only mode for exploration",
            "accept-edits": "Auto-approves file edit tools only",
            "auto-approve": "Auto-approves all tool executions",
        }.get(mode, "Unknown"),
    }


@server.tool()
async def vibe_configure_provider(
    ctx: Context,
    name: str,
    api_base: str,
    api_key_env_var: str,
    api_style: str = "openai",
    backend: str = "generic",
) -> dict[str, Any]:
    """Add or update a provider configuration (runtime only).

    Args:
        name: Provider identifier
        api_base: Base URL for API calls
        api_key_env_var: Environment variable for API key
        api_style: API style - "mistral", "openai", or "anthropic"
        backend: Backend implementation - "mistral", "generic", or "anthropic"

    Returns:
        Confirmation with provider details

    """
    config = get_vibe_config()

    try:
        new_provider = ProviderConfig(
            name=name,
            api_base=api_base,
            api_key_env_var=api_key_env_var,
            api_style=api_style,  # type: ignore
            backend=backend,  # type: ignore
        )
    except Exception as e:
        return {
            "success": False,
            "error": f"Invalid provider configuration: {e}",
        }

    # Check if provider already exists
    existing = config.get_provider(name)
    if existing:
        # Update existing (remove and re-add)
        config.providers = [p for p in config.providers if p.name != name]

    config.providers.append(new_provider)
    logger.info(f"[VIBE] Added/updated provider: {name}")

    return {
        "success": True,
        "provider": name,
        "api_base": api_base,
        "available": new_provider.is_available(),
        "note": "This change is runtime-only. Add to vibe_config.toml for persistence.",
    }


@server.tool()
async def vibe_session_resume(
    ctx: Context,
    session_id: str,
    prompt: str | None = None,
    cwd: str | None = None,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    """Resume a previous Vibe session.

    Args:
        session_id: Session ID to resume (partial match supported)
        prompt: Optional new prompt to continue with
        cwd: Working directory
        timeout_s: Timeout in seconds

    Returns:
        Result of the resumed session

    """
    # Verify session exists
    target_path = None

    # Search in session directory
    if VIBE_SESSION_DIR.exists():
        files = list(VIBE_SESSION_DIR.glob(f"*{session_id}*.json"))
        if files:
            target_path = files[0]

    if not target_path:
        return {
            "success": False,
            "error": f"Session '{session_id}' not found",
            "hint": "Use vibe_list_sessions to see available sessions",
        }

    # Extract full session ID from filename
    full_session_id = target_path.stem.replace("session_", "")

    # Use vibe_prompt with session continuation
    return cast(
        dict[str, Any],
        await vibe_prompt(
            ctx=ctx,
            prompt=prompt or "Continue from where we left off.",
            cwd=cwd,
            timeout_s=timeout_s,
            session_id=full_session_id,
        ),
    )


# =============================================================================
# MCP TOOLS - UTILITY (5 tools)
# =============================================================================


@server.tool()
async def vibe_ask(
    ctx: Context,
    question: str,
    cwd: str | None = None,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    """Ask Vibe AI a quick question (read-only, no tool execution).

    Args:
        question: The question to ask
        cwd: Working directory
        timeout_s: Timeout in seconds (default: 300)

    Returns:
        AI response without file modifications

    """
    return cast(
        dict[str, Any],
        await vibe_prompt(
            ctx=ctx,
            prompt=question,
            cwd=cwd,
            timeout_s=timeout_s or 300,
            mode="plan",
            max_turns=3,
            output_format="json",
        ),
    )


@server.tool()
async def vibe_execute_subcommand(
    ctx: Context,
    subcommand: str,
    args: list[str] | None = None,
    cwd: str | None = None,
    timeout_s: float | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute a specific Vibe CLI subcommand (utility operations).

    For AI interactions, use vibe_prompt() instead.

    Allowed subcommands:
        list-editors, list-modules, run, enable, disable, install,
        agent-reset, agent-on, agent-off, vibe-status, vibe-continue,
        vibe-cancel, vibe-help, eternal-engine, screenshots

    Args:
        subcommand: The Vibe subcommand
        args: Optional arguments
        cwd: Working directory
        timeout_s: Timeout in seconds
        env: Additional environment variables

    Returns:
        Command output and exit code

    """
    vibe_path = resolve_vibe_binary()
    if not vibe_path:
        return {"success": False, "error": "Vibe CLI not found"}

    sub = (subcommand or "").strip()
    if not sub:
        return {"success": False, "error": "Missing subcommand"}

    if sub in BLOCKED_SUBCOMMANDS:
        return {
            "success": False,
            "error": f"Subcommand '{sub}' is interactive and blocked",
            "suggestion": "Use vibe_prompt() for AI interactions",
        }

    if sub not in ALLOWED_SUBCOMMANDS:
        return {
            "success": False,
            "error": f"Unknown subcommand: '{sub}'",
            "allowed": sorted(ALLOWED_SUBCOMMANDS),
        }

    argv = [vibe_path, sub]
    if args:
        # Filter out interactive arguments
        clean_args = [str(a) for a in args if a != "--no-tui"]
        argv.extend(clean_args)

    # Create preview from subcommand and args
    preview = f"{sub} {' '.join(str(a) for a in (args or []))[:50]}"

    return await run_vibe_subprocess(
        argv=argv,
        cwd=cwd,
        timeout_s=timeout_s or DEFAULT_TIMEOUT_S,
        env=env,
        ctx=ctx,
        prompt_preview=preview,
    )


@server.tool()
async def vibe_list_sessions(ctx: Context, limit: int = 10) -> dict[str, Any]:
    """List recent Vibe session logs with metrics.

    Useful for tracking costs, context size, and session IDs for resuming.

    Args:
        limit: Number of sessions to return (default: 10)

    Returns:
        List of recent sessions with metadata

    """
    if not VIBE_SESSION_DIR.exists():
        return {
            "success": False,
            "error": f"Session directory not found at {VIBE_SESSION_DIR}",
        }

    try:
        files = sorted(
            VIBE_SESSION_DIR.glob("session_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )[:limit]

        sessions = []
        for f in files:
            try:
                with open(f, encoding="utf-8") as jf:
                    data = json.load(jf)
                    meta = data.get("metadata", {})
                    stats = meta.get("stats", {})

                    sessions.append(
                        {
                            "session_id": meta.get("session_id"),
                            "timestamp": meta.get("start_time"),
                            "steps": stats.get("steps", 0),
                            "prompt_tokens": stats.get("session_prompt_tokens", 0),
                            "completion_tokens": stats.get("session_completion_tokens", 0),
                            "file": f.name,
                        },
                    )
            except Exception as e:
                logger.debug(f"Failed to parse session {f.name}: {e}")

        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions),
        }

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return {
            "success": False,
            "error": f"Failed to list sessions: {e}",
        }


@server.tool()
async def vibe_session_details(ctx: Context, session_id_or_file: str) -> dict[str, Any]:
    """Get full details of a specific Vibe session.

    Args:
        session_id_or_file: Session ID or filename

    Returns:
        Full session details including history and token counts

    """
    target_path = None

    # Check absolute path
    if os.path.isabs(session_id_or_file) and os.path.exists(session_id_or_file):
        target_path = Path(session_id_or_file)

    # Check in session directory
    elif (VIBE_SESSION_DIR / session_id_or_file).exists():
        target_path = VIBE_SESSION_DIR / session_id_or_file

    # Search by pattern
    else:
        files = list(VIBE_SESSION_DIR.glob(f"*{session_id_or_file}*.json"))
        if files:
            target_path = files[0]

    if not target_path:
        return {
            "success": False,
            "error": f"Session '{session_id_or_file}' not found",
        }

    try:
        with open(target_path, encoding="utf-8") as f:
            data = json.load(f)
            return {
                "success": True,
                "data": data,
            }
    except Exception as e:
        logger.error(f"Failed to read session: {e}")
        return {
            "success": False,
            "error": f"Failed to read session: {e}",
        }


@server.tool()
async def vibe_reload_config(ctx: Context) -> dict[str, Any]:
    """Reload the Vibe configuration from disk.

    Returns:
        New configuration summary

    """
    global _current_mode, _current_model

    try:
        config = reload_vibe_config()

        # Reset runtime overrides
        _current_mode = config.default_mode
        _current_model = None

        return {
            "success": True,
            "active_model": config.active_model,
            "mode": config.default_mode.value,
            "providers_count": len(config.providers),
            "models_count": len(config.models),
        }
    except Exception as e:
        logger.error(f"Failed to reload config: {e}")
        return {
            "success": False,
            "error": f"Failed to reload config: {e}",
        }


# =============================================================================
# MCP TOOLS - DATABASE (2 tools)
# =============================================================================


@server.tool()
async def vibe_check_db(ctx: Context, query: str) -> dict[str, Any]:
    """Execute a read-only SQL SELECT query against the AtlasTrinity database.

    CRITICAL: This tool ONLY accepts valid SQL SELECT statements.
    Do NOT pass natural language goals, tasks, or questions here.
    For AI assistance or general questions, use 'vibe_prompt' or 'vibe_ask'.

    SCHEMA:
    - sessions: id, started_at, ended_at
    - tasks: id, session_id, goal, status, created_at
    - task_steps: id, task_id, sequence_number, action, tool, status, error_message
    - tool_executions: id, step_id, server_name, tool_name, arguments, result
    - logs: timestamp, level, source, message

    Args:
        query: A valid SQL SELECT statement.

    Returns:
        Query results as list of dictionaries

    """
    from sqlalchemy import text

    from src.brain.db.manager import db_manager

    # Basic SQL validation
    clean_query = query.strip().upper()

    # 1. Reject natural language (heuristic: many words, no SQL-specific structure)
    words = query.split()
    if len(words) > 5 and not any(k in clean_query for k in ["SELECT", "FROM", "WHERE", "JOIN"]):
        return {
            "success": False,
            "error": "This tool requires a SQL query, not natural language. For tasks or questions, use 'vibe_prompt' or 'vibe_ask'.",
            "hint": f"Your input looked like a goal: '{query[:50]}...'",
        }

    # 2. Enforce SELECT only
    if not clean_query.startswith("SELECT"):
        return {
            "success": False,
            "error": "Only SELECT queries are allowed for safety and read-only access.",
        }

    # 3. Prevent destructive operations
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE"]
    if any(re.search(rf"\b{f}\b", clean_query) for f in forbidden):
        return {
            "success": False,
            "error": "Forbidden keyword detected in query. Only read-only SELECT is allowed.",
        }

    # Use central DB manager when available
    try:
        await db_manager.initialize()
        if not db_manager.available:
            return {"success": False, "error": "Database not initialized"}

        session = await db_manager.get_session()
        try:
            res = await session.execute(text(query))
            rows = [dict(r) for r in res.mappings().all()]
            return {"success": True, "count": len(rows), "data": rows}
        finally:
            await session.close()

    except Exception as e:
        logger.error(f"Database query error: {e}")
        return {"success": False, "error": str(e)}


@server.tool()
async def vibe_get_system_context(ctx: Context) -> dict[str, Any]:
    """Retrieve current operational context from the database.

    Helps Vibe focus on the current state before performing deep analysis.

    Returns:
        Current session, recent tasks, and errors

    """
    from sqlalchemy import text

    from src.brain.db.manager import db_manager

    try:
        await db_manager.initialize()
        if not db_manager.available:
            return {"success": False, "error": "Database not initialized"}

        db_session = await db_manager.get_session()
        try:
            # Latest session
            res = await db_session.execute(
                text("SELECT id, started_at FROM sessions ORDER BY started_at DESC LIMIT 1"),
            )
            session_row = res.mappings().first()
            session_id = str(session_row["id"]) if session_row else None

            # Latest tasks
            tasks = []
            if session_id:
                tasks_res = await db_session.execute(
                    text(
                        "SELECT id, goal, status, created_at FROM tasks WHERE session_id = :sid ORDER BY created_at DESC LIMIT 5",
                    ),
                    {"sid": session_id},
                )
                tasks = [dict(r) for r in tasks_res.mappings().all()]

            # Recent errors
            errors_res = await db_session.execute(
                text(
                    "SELECT timestamp, source, message FROM logs WHERE level IN ('ERROR', 'WARNING') ORDER BY timestamp DESC LIMIT 5",
                ),
            )
            errors = [dict(r) for r in errors_res.mappings().all()]

            return {
                "success": True,
                "current_session_id": session_id,
                "recent_tasks": tasks,
                "recent_errors": errors,
                "system_root": SYSTEM_ROOT,
                "project_root": VIBE_WORKSPACE,
            }
        finally:
            await db_session.close()
    except Exception as e:
        logger.error(f"Database query error in vibe_get_system_context: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    logger.info("[VIBE] MCP Server starting (v3.0 Hyper-Refactored)...")
    prepare_workspace_and_instructions()
    cleanup_old_instructions()

    # Pre-load configuration
    try:
        config = get_vibe_config()
        logger.info(
            f"[VIBE] Configuration loaded: {len(config.models)} models, {len(config.providers)} providers",
        )
    except Exception as e:
        logger.warning(f"[VIBE] Could not load configuration: {e}")

    try:
        server.run()
    except (BrokenPipeError, KeyboardInterrupt):
        logger.info("[VIBE] Server shutdown requested")
        sys.exit(0)
    except ExceptionGroup as eg:
        if any(isinstance(e, BrokenPipeError) or "Broken pipe" in str(e) for e in eg.exceptions):
            sys.exit(0)
        logger.error(f"[VIBE] Unexpected error group: {eg}")
        raise
    except BaseException as e:
        if isinstance(e, BrokenPipeError) or "Broken pipe" in str(e):
            sys.exit(0)
        logger.error(f"[VIBE] Unexpected error: {e}")
        raise
