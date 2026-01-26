import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server import FastMCP, Server
from mcp.types import TextContent, Tool

# Import universal modules for external project support
try:
    from .diagram_generator import generate_architecture_diagram
    from .git_manager import ensure_git_repository, get_git_changes, setup_github_remote
    from .project_analyzer import analyze_project_structure, detect_changed_components
except ImportError:
    # Fallback for direct execution
    from diagram_generator import generate_architecture_diagram
    from git_manager import ensure_git_repository, get_git_changes, setup_github_remote
    from project_analyzer import analyze_project_structure, detect_changed_components

# Initialize FastMCP server
server = FastMCP("devtools-server")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


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
            return data
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
    """Run 'oxlint' on a specific file or directory (for JS/TS).
    Returns structured JSON results.
    """
    if not shutil.which("oxlint"):
        return {"error": "oxlint is not installed or not in PATH."}

    try:
        # oxlint --format json
        cmd = ["oxlint", "--format", "json", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        output = result.stdout.strip()
        if not output:
            return {"success": True, "violations": []}

        try:
            data = json.loads(output)
            # Oxlint JSON format is typically an array of objects
            violations = data if isinstance(data, list) else data.get("messages", [])
            return {
                "success": len(violations) == 0,
                "violation_count": len(violations),
                "violations": violations,
            }
        except json.JSONDecodeError:
            return {"error": "Failed to parse oxlint JSON output", "raw_output": output}

    except Exception as e:
        return {"error": str(e)}


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
def devtools_update_architecture_diagrams(
    project_path: str | None = None,
    commits_back: int = 1,
    target_mode: str = "internal",
    github_repo: str | None = None,
    github_token: str | None = None,
    init_git: bool = True,
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

    Args:
        project_path: Path to project. None = AtlasTrinity internal project
        commits_back: Number of commits to analyze for changes (default: 1)
        target_mode: 'internal' (AtlasTrinity) or 'external' (other projects)
        github_repo: GitHub repo name (e.g., 'user/repo') for remote setup
        github_token: GitHub token (reads from .env if not provided)
        init_git: Auto-initialize git if not present (default: True)

    Returns:
        Status of diagram updates with file locations, git status, GitHub config
    """
    import asyncio
    from datetime import datetime

    # Determine project paths
    if project_path is None:
        project_path_obj = PROJECT_ROOT
        target_mode = "internal"
    else:
        project_path_obj = Path(project_path).resolve()

    if not project_path_obj.exists():
        return {"error": f"Project path does not exist: {project_path_obj}", "success": False}

    response = {"success": True, "git_status": {}, "github_status": {}, "diagram_status": {}}

    try:
        # Step 1: Analyze project structure (UNIVERSAL)
        project_analysis = analyze_project_structure(project_path_obj)
        response["project_type"] = project_analysis.get("project_type", "unknown")
        response["components_detected"] = len(project_analysis.get("components", []))

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

        git_diff = git_changes.get("diff", "")
        modified_files = git_changes.get("modified_files", [])

        # Step 5: Detect affected components (UNIVERSAL)
        affected_components = detect_changed_components(project_analysis, git_diff, modified_files)

        response["analysis"] = {
            "modified_files": modified_files,
            "affected_components": affected_components,
            "has_changes": len(modified_files) > 0 or len(affected_components) > 0,
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

        response["message"] = "Architecture diagrams updated successfully"
        response["updates_made"] = True
        response["files_updated"] = updated_files
        response["timestamp"] = datetime.now().isoformat()

        return response

    except Exception as e:
        return {"error": f"Failed to update diagrams: {e}", "success": False}


# Old hardcoded functions removed - replaced by universal modules:
# - project_analyzer.py: analyze_project_structure, detect_changed_components
# - diagram_generator.py: generate_architecture_diagram
# - git_manager.py: ensure_git_repository, setup_github_remote, get_git_changes


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
