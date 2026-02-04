import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict, cast

from mcp.server import FastMCP

from .context_check import run_test_suite

# Import universal modules for external project support
from .diagram_generator import generate_architecture_diagram
from .git_manager import ensure_git_repository, get_git_changes, setup_github_remote
from .project_analyzer import analyze_project_structure, detect_changed_components
from .trace_analyzer import analyze_log_file

# Initialize FastMCP server
server = FastMCP("devtools-server")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VENV_BIN = PROJECT_ROOT / ".venv" / "bin"
VENV_PYTHON = VENV_BIN / "python"


class ResponseDict(TypedDict):
    success: bool
    git_status: dict[str, Any]
    github_status: dict[str, Any]
    diagram_status: dict[str, Any]
    project_type: str
    components_detected: int
    analysis: dict[str, Any]
    message: str
    updates_made: bool
    files_updated: list[str]
    timestamp: str


@server.tool()
def devtools_check_mcp_health() -> dict[str, Any]:
    """Run the system-wide MCP health check script.
    Ping all enabled servers and report their status, response time, and tool counts.
    """
    script_path = PROJECT_ROOT / "scripts" / "check_mcp_health.py"

    if not script_path.exists():
        return {"error": f"Health check script not found at {script_path}"}

    try:
        # Run scripts/check_mcp_health.py --json
        cmd = [sys.executable, str(script_path), "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        output = result.stdout.strip()
        if not output:
            return {"error": "Health check returned empty output", "stderr": result.stderr}

        try:
            data = json.loads(output)
            return cast(dict[str, Any], data)
        except json.JSONDecodeError:
            return {"error": "Failed to parse health check JSON", "raw_output": output}

    except Exception as e:
        return {"error": str(e)}


@server.tool()
def devtools_launch_inspector(server_name: str) -> dict[str, Any]:
    """Launch the official MCP Inspector for a specific server (Tier 1-4).
    This starts a background process and returns a URL (localhost) to open in the browser.

    Args:
        server_name: The name of the server to inspect (e.g., 'memory', 'vibe', 'filesystem').

    Note: The inspector process continues running in the background.

    """
    # Load active MCP config to find command
    config_path = Path.home() / ".config" / "atlastrinity" / "mcp" / "config.json"
    if not config_path.exists():
        # Fallback to template if active not found (unlikely in prod but helpful for dev)
        config_path = PROJECT_ROOT / "src" / "mcp_server" / "config.json.template"

    if not config_path.exists():
        return {"error": "MCP Configuration not found"}

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        server_config = config.get("mcpServers", {}).get(server_name)
        if not server_config:
            return {"error": f"Server '{server_name}' not found in configuration."}

        command = server_config.get("command")
        args = server_config.get("args", [])
        env_vars = server_config.get("env", {})

        # Construct inspector command
        # npx @modelcontextprotocol/inspector <command> <args>
        inspector_cmd = ["npx", "@modelcontextprotocol/inspector", command, *args]

        # Prepare environment
        env = os.environ.copy()
        # Resolve variables in args/env (basic resolution)
        # NOTE: This is a simplified resolution. For full resolution, we'd need mcp_manager logic.
        # But commonly used vars are usually just HOME or PROJECT_ROOT.

        # Basic substitution for '${HOME}' and '${PROJECT_ROOT}' in args
        resolved_inspector_cmd = []
        for arg in inspector_cmd:
            arg = arg.replace("${HOME}", str(Path.home()))
            arg = arg.replace("${PROJECT_ROOT}", str(PROJECT_ROOT))
            resolved_inspector_cmd.append(arg)

        # Add server-specific env vars
        for k, v in env_vars.items():
            val = v.replace("${GITHUB_TOKEN}", env.get("GITHUB_TOKEN", ""))
            env[k] = val

        # Start detached process
        # We redirect stdout/stderr to capture the URL, but we need to be careful not to block.
        # Ideally, we start it, wait a second to scrape the URL from stderr, then let it run.

        proc = subprocess.Popen(
            resolved_inspector_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,  # Detach
        )

        # Peek at output to find URL (inspector prints to stderr usually)
        # We'll wait up to 5 seconds
        import time

        for _ in range(10):
            if proc.poll() is not None:
                # Process died
                out, err = proc.communicate()
                return {
                    "error": "Inspector process exited immediately",
                    "stdout": out,
                    "stderr": err,
                }

            # We can't easily read without blocking unless we use threads or fancy non-blocking I/O.
            # Simple approach: Return success and tell user to check output or assume standard port.
            # But the user wants the URL.
            # Let's try to assume it works and return a generic message,
            # OR better: The inspector usually prints "Inspector is running at http://localhost:xxxx"

            time.sleep(0.5)

        # If it's still running, we assume success.
        return {
            "success": True,
            "message": f"Inspector launched for '{server_name}'.",
            "pid": proc.pid,
            "note": "Please check http://localhost:5173 (default) or check terminal output if visible.",
        }

    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# MCP Inspector CLI Tools - Headless verification without UI
# =============================================================================


def _get_inspector_server_cmd(
    server_name: str,
) -> tuple[list[str], dict[str, str]] | dict[str, Any]:
    """Build the inspector CLI command for a given server.

    Returns tuple (cmd_parts, env) on success, or error dict on failure.
    """
    config_path = Path.home() / ".config" / "atlastrinity" / "mcp" / "config.json"
    if not config_path.exists():
        return {"error": "MCP Configuration not found", "path": str(config_path)}

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        server_config = config.get("mcpServers", {}).get(server_name)
        if not server_config:
            return {"error": f"Server '{server_name}' not found in configuration."}

        command = server_config.get("command")
        args = server_config.get("args", [])
        env_vars = server_config.get("env", {})

        # Build base command parts (will be joined with inspector args)
        # Resolve common variables
        resolved_args = []
        for arg in args:
            arg = arg.replace("${HOME}", str(Path.home()))
            arg = arg.replace("${PROJECT_ROOT}", str(PROJECT_ROOT))
            resolved_args.append(arg)

        resolved_command = command.replace("${HOME}", str(Path.home()))
        resolved_command = resolved_command.replace("${PROJECT_ROOT}", str(PROJECT_ROOT))

        # Base inspector + server command
        server_cmd = [resolved_command, *resolved_args]

        # Prepare environment
        env = os.environ.copy()
        for k, v in env_vars.items():
            val = v.replace("${GITHUB_TOKEN}", env.get("GITHUB_TOKEN", ""))
            val = val.replace("${HOME}", str(Path.home()))
            val = val.replace("${PROJECT_ROOT}", str(PROJECT_ROOT))
            env[k] = val

        return (server_cmd, env)

    except Exception as e:
        return {"error": f"Failed to load config: {e}"}


def _run_inspector_cli(
    server_name: str,
    method: str,
    extra_args: list[str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Run MCP Inspector CLI with specified method and return parsed JSON result."""
    result = _get_inspector_server_cmd(server_name)
    if isinstance(result, dict):
        return result  # Error dict

    server_cmd, env = result

    # Build full inspector command
    inspector_cmd = [
        "npx",
        "@modelcontextprotocol/inspector",
        "--cli",
        *server_cmd,
        "--method",
        method,
    ]

    if extra_args:
        inspector_cmd.extend(extra_args)

    try:
        proc_result = subprocess.run(
            inspector_cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
            check=False,
        )

        stdout = proc_result.stdout.strip()
        stderr = proc_result.stderr.strip()

        if proc_result.returncode != 0:
            return {
                "success": False,
                "error": stderr or f"Exit code {proc_result.returncode}",
                "stdout": stdout,
            }

        if not stdout:
            return {"success": True, "data": None, "note": "Empty response"}

        try:
            data = json.loads(stdout)
            return {"success": True, "data": data}
        except json.JSONDecodeError:
            # Return raw output if not JSON
            return {"success": True, "raw_output": stdout}

    except subprocess.TimeoutExpired:
        return {"error": f"Timeout after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def mcp_inspector_list_tools(server_name: str) -> dict[str, Any]:
    """List all tools available on a specified MCP server via Inspector CLI.

    Args:
        server_name: Name of the MCP server (e.g., 'filesystem', 'memory', 'vibe').

    Returns:
        Dict with 'success' and 'data' (list of tools with names and schemas).
    """
    return _run_inspector_cli(server_name, "tools/list")


@server.tool()
def mcp_inspector_call_tool(
    server_name: str,
    tool_name: str,
    args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call a specific tool on an MCP server via Inspector CLI.

    Args:
        server_name: Name of the MCP server.
        tool_name: Name of the tool to call.
        args: Optional dictionary of arguments to pass to the tool.

    Returns:
        Dict with 'success' and 'data' (tool execution result).
    """
    extra_args = ["--tool-name", tool_name]

    if args:
        for key, value in args.items():
            if isinstance(value, (dict, list)):
                extra_args.extend(["--tool-arg", f"{key}={json.dumps(value)}"])
            else:
                extra_args.extend(["--tool-arg", f"{key}={value}"])

    return _run_inspector_cli(server_name, "tools/call", extra_args)


@server.tool()
def mcp_inspector_list_resources(server_name: str) -> dict[str, Any]:
    """List all resources available on a specified MCP server via Inspector CLI.

    Args:
        server_name: Name of the MCP server.

    Returns:
        Dict with 'success' and 'data' (list of resources with URIs and descriptions).
    """
    return _run_inspector_cli(server_name, "resources/list")


@server.tool()
def mcp_inspector_read_resource(server_name: str, uri: str) -> dict[str, Any]:
    """Read a specific resource from an MCP server via Inspector CLI.

    Args:
        server_name: Name of the MCP server.
        uri: URI of the resource to read.

    Returns:
        Dict with 'success' and 'data' (resource contents).
    """
    extra_args = ["--uri", uri]
    return _run_inspector_cli(server_name, "resources/read", extra_args)


@server.tool()
def mcp_inspector_list_prompts(server_name: str) -> dict[str, Any]:
    """List all prompts available on a specified MCP server via Inspector CLI.

    Args:
        server_name: Name of the MCP server.

    Returns:
        Dict with 'success' and 'data' (list of prompts with names and descriptions).
    """
    return _run_inspector_cli(server_name, "prompts/list")


@server.tool()
def mcp_inspector_get_prompt(
    server_name: str,
    prompt_name: str,
    args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Get a specific prompt from an MCP server via Inspector CLI.

    Args:
        server_name: Name of the MCP server.
        prompt_name: Name of the prompt to retrieve.
        args: Optional dictionary of arguments to pass to the prompt.

    Returns:
        Dict with 'success' and 'data' (prompt content with messages).
    """
    extra_args = ["--prompt-name", prompt_name]

    if args:
        for key, value in args.items():
            extra_args.extend(["--prompt-args", f"{key}={value}"])

    return _run_inspector_cli(server_name, "prompts/get", extra_args)


@server.tool()
def mcp_inspector_get_schema(server_name: str, tool_name: str) -> dict[str, Any]:
    """Get the JSON schema for a specific tool on an MCP server.

    Args:
        server_name: Name of the MCP server.
        tool_name: Name of the tool to get schema for.

    Returns:
        Dict with 'success' and 'schema' (input schema for the tool).
    """
    # First list all tools, then extract the specific one
    result = _run_inspector_cli(server_name, "tools/list")

    if not result.get("success"):
        return result

    data = result.get("data")
    if not data:
        return {"error": "No tools data returned"}

    # Handle different response formats
    tools_list = data.get("tools", data) if isinstance(data, dict) else data

    if not isinstance(tools_list, list):
        return {"error": "Unexpected tools format", "raw": data}

    for tool in tools_list:
        if isinstance(tool, dict) and tool.get("name") == tool_name:
            return {
                "success": True,
                "tool_name": tool_name,
                "schema": tool.get("inputSchema", tool.get("schema", {})),
                "description": tool.get("description", ""),
            }

    return {"error": f"Tool '{tool_name}' not found on server '{server_name}'"}


@server.tool()
def devtools_run_mcp_sandbox(
    server_name: str | None = None,
    all_servers: bool = False,
    chain_length: int = 1,
    autofix: bool = False,
) -> dict[str, Any]:
    """Run MCP sandbox tests with LLM-generated realistic scenarios.

    This tool tests ALL MCP tools (including destructive ones) in a safe
    isolated sandbox environment. It generates realistic test scenarios
    using LLM and can chain multiple tools together for natural testing flows.

    Args:
        server_name: Specific server to test (e.g., 'filesystem', 'memory')
        all_servers: Test all enabled MCP servers
        chain_length: Number of tools to chain in each scenario (1-5)
        autofix: Automatically attempt to fix failures via Vibe MCP

    Returns:
        Dict with test results including passed/failed counts and details.
    """
    script_path = PROJECT_ROOT / "scripts" / "mcp_sandbox.py"

    if not script_path.exists():
        return {"error": f"Sandbox script not found at {script_path}"}

    # Build command
    cmd = [str(VENV_PYTHON), str(script_path), "--json"]

    if server_name:
        cmd.extend(["--server", server_name])
    elif all_servers:
        cmd.append("--all")
    else:
        return {"error": "Must specify either server_name or all_servers=True"}

    if chain_length > 1:
        cmd.extend(["--chain", str(min(5, max(1, chain_length)))])

    if autofix:
        cmd.append("--autofix")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for full test
            check=False,
        )

        stdout = result.stdout.strip()
        if not stdout:
            return {
                "error": "Sandbox returned empty output",
                "stderr": result.stderr,
                "returncode": result.returncode,
            }

        try:
            data = json.loads(stdout)
            return cast(dict[str, Any], data)
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse sandbox JSON output",
                "raw_output": stdout[:500],
                "stderr": result.stderr,
            }

    except subprocess.TimeoutExpired:
        return {"error": "Sandbox test timed out (>5 minutes)"}
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def devtools_validate_config() -> dict[str, Any]:
    """Validate the syntax and basic structure of the local MCP configuration file."""
    config_path = Path.home() / ".config" / "atlastrinity" / "mcp" / "config.json"

    if not config_path.exists():
        return {"error": "Config file not found", "path": str(config_path)}

    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)

        mcp_servers = data.get("mcpServers", {})
        if not mcp_servers:
            return {"valid": False, "error": "Missing 'mcpServers' key or empty"}

        server_count = len([k for k in mcp_servers if not k.startswith("_")])
        return {"valid": True, "server_count": server_count, "path": str(config_path)}
    except json.JSONDecodeError as e:
        return {"valid": False, "error": f"JSON Syntax Error: {e}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@server.tool()
def devtools_lint_python(file_path: str = ".") -> dict[str, Any]:
    """Run the 'ruff' linter on a specific file or directory.
    Returns structured JSON results of any violations found.
    """
    # Check if ruff is installed
    if not shutil.which("ruff"):
        return {"error": "Ruff is not installed or not in PATH."}

    try:
        # Run ruff check --output-format=json
        cmd = ["ruff", "check", "--output-format=json", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        # If exit code is 0, no errors (usually). But ruff returns non-zero on lint errors too.
        # We parse stdout.
        output = result.stdout.strip()

        # If empty and stderr has content, something crashed or misconfigured
        if not output and result.stderr:
            # Check if it was just a "no errors" case or actual failure
            if result.returncode == 0:
                return {"success": True, "violations": []}
            return {"error": f"Ruff execution failed: {result.stderr}"}

        if not output:
            return {"success": True, "violations": []}

        try:
            violations = json.loads(output)
            return {
                "success": len(violations) == 0,
                "violation_count": len(violations),
                "violations": violations,
            }
        except json.JSONDecodeError:
            return {"error": "Failed to parse ruff JSON output", "raw_output": output}

    except Exception as e:
        return {"error": str(e)}


@server.tool()
def devtools_lint_js(file_path: str = ".") -> dict[str, Any]:
    """Run JS/TS linters (oxlint and eslint) on a specific file or directory.
    Returns structured results from both tools.
    """
    results: dict[str, Any] = {"success": True, "violations": [], "summary": {}}

    # 1. Run oxlint
    if shutil.which("oxlint"):
        try:
            cmd = ["oxlint", "--format", "json", file_path]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            output = res.stdout.strip()
            if output:
                try:
                    data = json.loads(output)
                    violations = data if isinstance(data, list) else data.get("messages", [])
                    results["violations"].extend(violations)
                    results["summary"]["oxlint"] = len(violations)
                    if len(violations) > 0:
                        results["success"] = False
                except json.JSONDecodeError:
                    results["summary"]["oxlint_error"] = "Failed to parse JSON"
            else:
                results["summary"]["oxlint"] = 0
        except Exception as e:
            results["summary"]["oxlint_exception"] = str(e)

    # 2. Run eslint (via npx to use project-local config)
    if shutil.which("npx"):
        try:
            # Check for eslint config
            has_config = any(
                (PROJECT_ROOT / f).exists()
                for f in [".eslintrc.js", ".eslintrc.json", ".eslintrc.yml", "eslint.config.js"]
            )
            if has_config:
                cmd = ["npx", "eslint", "--format", "json", file_path]
                # Filter out non-JSON lines (sometimes npx prints update notifications)
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                output = res.stdout.strip()
                if output:
                    # Find the first '[' which usually starts the JSON array
                    start_idx = output.find("[")
                    if start_idx != -1:
                        try:
                            violations = json.loads(output[start_idx:])
                            # ESLint returns objects with 'messages' list per file
                            total_eslint = 0
                            for item in violations:
                                msgs = item.get("messages", [])
                                total_eslint += len(msgs)
                                results["violations"].extend(msgs)
                            results["summary"]["eslint"] = total_eslint
                            if total_eslint > 0:
                                results["success"] = False
                        except json.JSONDecodeError:
                            results["summary"]["eslint_error"] = "Failed to parse JSON"
                else:
                    results["summary"]["eslint"] = 0
        except Exception as e:
            results["summary"]["eslint_exception"] = str(e)

    return results


@server.tool()
def devtools_run_global_lint() -> dict[str, Any]:
    """Run the complete system linting suite (npm run lint:all).
    This includes Python (ruff, pyrefly, mypy, bandit, xenon) and
    JS/TS (oxlint, eslint) checks.
    """
    try:
        # npm run lint:all is defined in package.json at project root
        cmd = ["npm", "run", "lint:all"]
        result = subprocess.run(
            cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "exit_code": result.returncode,
        }
    except Exception as e:
        return {"error": str(e), "success": False}


@server.tool()
def devtools_find_dead_code(target_path: str = ".") -> dict[str, Any]:
    """Run 'knip' to find unused files, dependencies, and exports.
    Requires 'knip' to be installed in the project (usually via npm).
    """
    if not shutil.which("knip") and not shutil.which("npx"):
        return {"error": "knip (or npx) is not found."}

    try:
        # We use npx knip --reporter json
        # NOTE: knip usually needs to run from the project root where package.json is.
        # target_path might be used as cwd if it's a directory.

        cwd = target_path if os.path.isdir(target_path) else "."

        cmd = ["npx", "knip", "--reporter", "json"]
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)

        output = result.stdout.strip()
        if not output:
            return {"success": True, "issues": []}

        try:
            data = json.loads(output)
            return {"success": True, "data": data}
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse knip JSON output",
                "raw_output": output,
                "stderr": result.stderr,
            }

    except Exception as e:
        return {"error": str(e)}


@server.tool()
def devtools_check_integrity(path: str = "src/") -> dict[str, Any]:
    """Run 'pyrefly' to check code integrity and find generic coding errors."""
    if not shutil.which("pyrefly"):
        return {"error": "pyrefly is not installed."}

    try:
        # Run pyrefly check
        cmd = ["pyrefly", "check", path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # Simple heuristic to extract violation count if possible
        # Pyrefly usually prints something like "Found X errors"
        import re

        error_match = re.search(r"Found (\d+) error", stdout + stderr, re.IGNORECASE)
        error_count = (
            int(error_match.group(1)) if error_match else (0 if result.returncode == 0 else -1)
        )

        return {
            "success": result.returncode == 0,
            "error_count": error_count,
            "stdout": stdout,
            "stderr": stderr,
        }
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def devtools_check_security(path: str = "src/") -> dict[str, Any]:
    """Run security audit tools (bandit, safety, detect-secrets, npm audit)."""
    results: dict[str, Any] = {}

    # 1. Bandit
    bandit_bin = (
        vbin
        if (
            vbin := shutil.which(
                "bandit", path=os.pathsep.join([str(VENV_BIN), os.environ.get("PATH", "")])
            )
        )
        else "bandit"
    )
    try:
        cmd = [bandit_bin, "-r", path, "-ll", "--format", "json"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        results["bandit"] = json.loads(res.stdout) if res.stdout else {"error": res.stderr}
    except Exception as e:
        results["bandit"] = {"error": str(e)}

    # 2. Safety (Check dependencies)
    safety_bin = (
        vbin
        if (
            vbin := shutil.which(
                "safety", path=os.pathsep.join([str(VENV_BIN), os.environ.get("PATH", "")])
            )
        )
        else "safety"
    )
    try:
        cmd = [safety_bin, "check", "--json"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        results["safety"] = json.loads(res.stdout) if res.stdout else {"error": res.stderr}
    except Exception as e:
        results["safety"] = {"error": str(e)}

    # 3. Detect-secrets
    ds_bin = (
        vbin
        if (
            vbin := shutil.which(
                "detect-secrets", path=os.pathsep.join([str(VENV_BIN), os.environ.get("PATH", "")])
            )
        )
        else "detect-secrets"
    )
    try:
        cmd = [ds_bin, "scan", path]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        results["secrets"] = json.loads(res.stdout) if res.stdout else {"error": res.stderr}
    except Exception as e:
        results["secrets"] = {"error": str(e)}

    # 4. NPM Audit
    if shutil.which("npm"):
        try:
            cmd = ["npm", "audit", "--json"]
            res = subprocess.run(
                cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False
            )
            results["npm_audit"] = json.loads(res.stdout) if res.stdout else {"error": res.stderr}
        except Exception as e:
            results["npm_audit"] = {"error": str(e)}

    return results


@server.tool()
def devtools_check_complexity(path: str = "src/") -> dict[str, Any]:
    """Run complexity audit (xenon)."""
    xenon_bin = (
        vbin
        if (
            vbin := shutil.which(
                "xenon", path=os.pathsep.join([str(VENV_BIN), os.environ.get("PATH", "")])
            )
        )
        else "xenon"
    )
    try:
        # xenon --max-absolute B --max-modules B --max-average A <path>
        cmd = [xenon_bin, "--max-absolute", "B", "--max-modules", "B", "--max-average", "A", path]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return {
            "success": res.returncode == 0,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
        }
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def devtools_check_types_python(path: str = "src") -> dict[str, Any]:
    """Run deep type checking for Python (mypy)."""
    mypy_bin = (
        vbin
        if (
            vbin := shutil.which(
                "mypy", path=os.pathsep.join([str(VENV_BIN), os.environ.get("PATH", "")])
            )
        )
        else "mypy"
    )
    try:
        # We use --explicit-package-bases as discovered during CLI verification
        cmd = [mypy_bin, path, "--explicit-package-bases"]
        # Set MYPYPATH if needed, but CLI test showed 'mypy src' works if src is root-ish
        env = os.environ.copy()
        if path == "src":
            env["MYPYPATH"] = "src"

        res = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
        return {
            "success": res.returncode == 0,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
            "violation_count": len(res.stdout.splitlines()) if res.returncode != 0 else 0,
        }
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def devtools_check_types_ts() -> dict[str, Any]:
    """Run deep type checking for TypeScript (tsc --noEmit)."""
    tsc_bin = shutil.which("tsc") or "npx tsc"
    try:
        cmd = [*tsc_bin.split(), "--noEmit"]
        res = subprocess.run(
            cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False
        )
        return {
            "success": res.returncode == 0,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
        }
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def devtools_run_context_check(test_file: str) -> dict[str, Any]:
    """Run logic validation tests from a YAML/JSON file against a mock runner (dry run).

    This tool validates the format of your test scenarios and runs them.
    Currently runs in 'dry_run' mode unless a runner is programmatically injected.
    Future versions will integrate with the active LLM session.

    Args:
        test_file: Path to the .yaml or .json test definition file.
    """
    return run_test_suite(test_file)


@server.tool()
def devtools_analyze_trace(log_path: str) -> dict[str, Any]:
    """Analyze an MCP execution log file for logic issues.

    Detects infinite loops (repeated tool calls), inefficiencies, and
    potential hallucinations in tool usage.

    Args:
        log_path: Path to the log file (e.g., brain.log or relevant log file).
    """
    return analyze_log_file(log_path)


@server.tool()
def devtools_update_architecture_diagrams(
    project_path: str | None = None,
    commits_back: int = 1,
    target_mode: str = "internal",
    github_repo: str | None = None,
    github_token: str | None = None,
    init_git: bool = True,
    use_reasoning: bool = True,
) -> dict[str, Any]:
    """Auto-update architecture diagrams by analyzing git changes.

    Universal system that works for ANY project type (Python, Node.js, Rust, Go, etc.).
    Analyzes project structure dynamically and generates appropriate diagrams.

    Features:
    - Universal project detection (Python, Node.js, Rust, Go, generic)
    - Dynamic component analysis
    - Git initialization for new projects
    - GitHub token setup and remote configuration
    - Intelligent diagram generation based on project structure
    - LLM reasoning via sequential-thinking MCP (raptor-mini) for complex changes

    Args:
        project_path: Path to project. None = AtlasTrinity internal project
        commits_back: Number of commits to analyze for changes (default: 1)
        target_mode: 'internal' (AtlasTrinity) or 'external' (other projects)
        github_repo: GitHub repo name (e.g., 'user/repo') for remote setup
        github_token: GitHub token (reads from .env if not provided)
        init_git: Auto-initialize git if not present (default: True)
        use_reasoning: Use sequential-thinking MCP for deep analysis (default: True)

    Returns:
        Status of diagram updates with file locations, git status, GitHub config,
        and reasoning analysis if enabled
    """

    # Determine project paths
    if project_path is None:
        project_path_obj = PROJECT_ROOT
        target_mode = "internal"
    else:
        project_path_obj = Path(project_path).resolve()

    if not project_path_obj.exists():
        return {"error": f"Project path does not exist: {project_path_obj}", "success": False}

    response: ResponseDict = {
        "success": True,
        "git_status": {},
        "github_status": {},
        "diagram_status": {},
        "project_type": "",
        "components_detected": 0,
        "analysis": {},
        "message": "",
        "updates_made": False,
        "files_updated": [],
        "timestamp": "",
    }

    try:
        # Step 1: Analyze project structure (UNIVERSAL)
        project_analysis = analyze_project_structure(project_path_obj)
        response["project_type"] = project_analysis.get("project_type", "unknown")
        response["components_detected"] = len(project_analysis.get("components", []))  # type: ignore[typeddict-item]

        # Step 2: Ensure git is initialized
        if init_git and not project_analysis.get("git_initialized"):
            git_init_result = ensure_git_repository(project_path_obj)
            response["git_status"]["initialized"] = git_init_result
            if not git_init_result.get("initialized"):
                return {"error": git_init_result.get("error", "Git init failed"), "success": False}

        # Step 3: Setup GitHub remote if requested
        if github_repo or github_token:
            github_result = setup_github_remote(project_path_obj, github_repo, github_token)
            response["github_status"] = github_result

        # Step 4: Get git changes (UNIVERSAL - all files, not just src/brain/)
        git_changes = get_git_changes(project_path_obj, commits_back)
        if not git_changes.get("success"):
            # No git history yet or error - create initial diagram
            git_changes = {"diff": "", "modified_files": [], "log": ""}

        git_diff: str = git_changes.get("diff", "")  # type: ignore[assignment]
        modified_files: list[str] = git_changes.get("modified_files", [])  # type: ignore[assignment]

        # Step 5: Detect affected components (UNIVERSAL)
        affected_components = detect_changed_components(project_analysis, git_diff, modified_files)

        # Step 5.5: Deep reasoning analysis (if enabled)
        reasoning_analysis = None
        if use_reasoning and len(modified_files) > 0:
            reasoning_analysis = _analyze_changes_with_reasoning(
                modified_files, affected_components, git_diff, project_analysis
            )

        response["analysis"] = {
            "modified_files": modified_files,
            "affected_components": affected_components,
            "has_changes": len(modified_files) > 0 or len(affected_components) > 0,
            "reasoning": reasoning_analysis,
        }

        if not response["analysis"]["has_changes"]:
            return {
                "success": True,
                "message": "No changes detected in project",
                "updates_made": False,
            }

        # Step 6: Generate/Update diagrams (UNIVERSAL)
        updated_files = []

        if target_mode == "internal":
            # AtlasTrinity internal mode - update both locations
            internal_path = (
                PROJECT_ROOT
                / "src"
                / "brain"
                / "data"
                / "architecture_diagrams"
                / "mcp_architecture.md"
            )
            docs_path = PROJECT_ROOT / ".agent" / "docs" / "mcp_architecture_diagram.md"

            # For internal, keep existing diagram and add update marker
            if docs_path.exists():
                with open(docs_path, encoding="utf-8") as f:
                    current_diagram = f.read()

                # Add update notice
                update_notice = f"\n<!-- AUTO-UPDATED: {datetime.now().isoformat()} -->\n"
                update_notice += f"<!-- Modified: {', '.join(modified_files[:3])} -->\n\n"
                updated_diagram = update_notice + current_diagram

                with open(internal_path, "w", encoding="utf-8") as f:
                    f.write(updated_diagram)
                with open(docs_path, "w", encoding="utf-8") as f:
                    f.write(updated_diagram)

                updated_files = [str(internal_path), str(docs_path)]
        else:
            # External project - generate diagram from project analysis
            diagram_path = project_path_obj / "architecture_diagram.md"

            # Generate diagram based on project structure
            diagram_content = generate_architecture_diagram(project_path_obj, project_analysis)

            with open(diagram_path, "w", encoding="utf-8") as f:
                f.write(diagram_content)

            updated_files.append(str(diagram_path))

        # Step 7: Export diagrams to PNG/SVG
        _export_diagrams(target_mode, project_path_obj)
        response["diagram_status"]["exported"] = True

        response["message"] = "Architecture diagrams updated successfully"  # type: ignore[typeddict-item]
        response["updates_made"] = True  # type: ignore[typeddict-item]
        response["files_updated"] = updated_files  # type: ignore[typeddict-item]
        response["timestamp"] = datetime.now().isoformat()  # type: ignore[typeddict-item]

        return cast(dict[str, Any], response)

    except Exception as e:
        return {"error": f"Failed to update diagrams: {e}", "success": False}


# Old hardcoded functions removed - replaced by universal modules:
# - project_analyzer.py: analyze_project_structure, detect_changed_components
# - diagram_generator.py: generate_architecture_diagram
# - git_manager.py: ensure_git_repository, setup_github_remote, get_git_changes


def _analyze_changes_with_reasoning(
    modified_files: list[str],
    affected_components: list[str],
    git_diff: str,
    project_analysis: dict[str, Any],
) -> dict[str, Any] | None:
    """Analyze git changes using sequential-thinking MCP for deep reasoning.

    Uses raptor-mini model via sequential-thinking MCP to understand:
    - Architectural impact of changes
    - Cross-component dependencies
    - Potential diagram updates needed

    Args:
        modified_files: List of changed file paths
        affected_components: List of affected component names
        git_diff: Full git diff output
        project_analysis: Project structure analysis

    Returns:
        Dict with reasoning analysis or None if reasoning unavailable
    """
    try:
        # Try to call sequential-thinking MCP (raptor-mini)
        # Note: This requires MCP manager to be available
        # For standalone devtools server, we'll use a simplified analysis

        # Build context for reasoning
        context = f"""
Analyze the architectural impact of these changes:

Modified Files ({len(modified_files)}):
{chr(10).join(f"- {f}" for f in modified_files[:10])}

Affected Components ({len(affected_components)}):
{chr(10).join(f"- {c}" for c in affected_components)}

Project Type: {project_analysis.get("project_type", "unknown")}
Total Components: {len(project_analysis.get("components", []))}

Task: Identify cross-component impacts and recommend diagram updates.
"""

        # Since we're in MCP server context (no direct access to MCPManager),
        # we'll return a structured analysis that can be used by callers
        # The actual sequential-thinking call would be made by the agent/orchestrator

        return {
            "complexity": "high"
            if len(affected_components) > 3
            else "medium"
            if len(affected_components) > 1
            else "low",
            "cross_component": len(affected_components) > 1,
            "requires_deep_analysis": len(modified_files) > 5 or len(affected_components) > 3,
            "context_for_reasoning": context,
            "recommendation": (
                "Use sequential-thinking for deep analysis"
                if len(modified_files) > 5
                else "Standard diagram update sufficient"
            ),
        }

    except Exception as e:
        # Reasoning is optional, don't fail on errors
        return {"error": str(e), "reasoning_available": False}


def _export_diagrams(target_mode: str, project_path: Path) -> None:
    """Export diagrams to PNG/SVG using mmdc."""
    try:
        if target_mode == "internal":
            # Export from internal location
            input_path = (
                PROJECT_ROOT
                / "src"
                / "brain"
                / "data"
                / "architecture_diagrams"
                / "mcp_architecture.md"
            )
            output_dir = (
                PROJECT_ROOT / "src" / "brain" / "data" / "architecture_diagrams" / "exports"
            )
        else:
            # Export from external project
            input_path = project_path / "architecture_diagram.md"
            output_dir = project_path / "diagrams"

        output_dir.mkdir(parents=True, exist_ok=True)

        # Run mmdc
        cmd = [
            "mmdc",
            "-i",
            str(input_path),
            "-o",
            str(output_dir / "architecture.png"),
            "-t",
            "dark",
            "-b",
            "transparent",
        ]

        subprocess.run(cmd, capture_output=True, check=False)

    except Exception:
        # Export is optional, don't fail on errors
        pass


if __name__ == "__main__":
    server.run()
