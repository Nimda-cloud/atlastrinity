"""
Terminal MCP Server

Exposes persistent terminal command execution capabilities.
Reads configuration from config.yaml under mcp.terminal section.
"""

import asyncio
import os
import shlex
import subprocess
from datetime import datetime
from typing import Any, Optional

from mcp.server import FastMCP

# Load config from YAML
try:
    from .config_loader import get_config_value

    MAX_COMMAND_LENGTH = get_config_value("terminal", "max_command_length", 1000)
    COMMAND_TIMEOUT = get_config_value("terminal", "command_timeout", 60)
except Exception:
    MAX_COMMAND_LENGTH = 1000
    COMMAND_TIMEOUT = 60

# Initialize FastMCP server
server = FastMCP("terminal")

# State
persistent_cwd = os.getcwd()


@server.tool()
async def execute_command(
    command: str,
    cwd: Optional[str] = None,
    stdout_file: Optional[str] = None,
    stderr_file: Optional[str] = None,
    capture_exit_code: bool = False,
    capture_timestamp: bool = False,
    **kwargs: Any,
) -> str:
    """
    Execute a terminal command in a persistent shell session (maintains CWD).

    Args:
        command: The shell command to run.
        cwd: Optional directory to run THIS command in (overrides persistent CWD).
        stdout_file: Optional path to save stdout to.
        stderr_file: Optional path to save stderr to.
        capture_exit_code: If true, includes exit code in the output.
        capture_timestamp: If true, includes start/end timestamps.
    """
    global persistent_cwd

    current_cwd = cwd or persistent_cwd
    start_time = datetime.now() if capture_timestamp else None

    try:
        if len(command) > int(MAX_COMMAND_LENGTH):
            return f"Command too long (>{MAX_COMMAND_LENGTH} chars)"

        # Check for cd command to handle it manually (subprocess doesn't persist cd)
        parts = shlex.split(command)
        if (
            parts and parts[0] == "cd" and not cwd
        ):  # Only update persistent CWD if per-command CWD is not provided
            if len(parts) > 1:
                target = parts[1]
                target = os.path.expanduser(target)
                new_dir = os.path.abspath(os.path.join(persistent_cwd, target))
                if os.path.isdir(new_dir):
                    persistent_cwd = new_dir
                    return f"Changed persistent directory to {persistent_cwd}"
                else:
                    return f"cd: {target}: No such file or directory"
            else:
                persistent_cwd = os.path.expanduser("~")
                return f"Changed persistent directory to {persistent_cwd}"

        # Execute other commands
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=current_cwd,
            env=os.environ.copy(),
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=float(COMMAND_TIMEOUT)
            )
            end_time = datetime.now() if capture_timestamp else None
        except asyncio.TimeoutError:
            try:
                process.kill()
            except Exception:
                pass
            return f"Command timed out after {COMMAND_TIMEOUT}s"

        output = stdout.decode().strip()
        error = stderr.decode().strip()
        exit_code = process.returncode

        # Save to files if requested
        if stdout_file:
            try:
                # Ensure directory exists
                out_path = os.path.abspath(os.path.join(current_cwd, stdout_file))
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w") as f:
                    f.write(output)
            except Exception as fe:
                error += f"\nFailed to save stdout to {stdout_file}: {fe}"

        if stderr_file:
            try:
                err_path = os.path.abspath(os.path.join(current_cwd, stderr_file))
                os.makedirs(os.path.dirname(err_path), exist_ok=True)
                with open(err_path, "w") as f:
                    f.write(error)
            except Exception as fe:
                error += f"\nFailed to save stderr to {stderr_file}: {fe}"

        res_parts = []
        if capture_timestamp and start_time and end_time:
            res_parts.append(
                f"Started: {start_time.isoformat()}\nFinished: {end_time.isoformat()}"
            )

        if output:
            res_parts.append(output)
        if error:
            res_parts.append(f"Error: {error}")

        if capture_exit_code:
            res_parts.append(f"Exit Code: {exit_code}")

        return "\n".join(res_parts) if res_parts else "(No output)"

    except Exception as e:
        return f"Execution failed: {str(e)}"


if __name__ == "__main__":
    server.run()
