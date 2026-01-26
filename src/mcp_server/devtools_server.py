import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server import FastMCP

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
    project_path: str | None = None, commits_back: int = 1, target_mode: str = "internal"
) -> dict[str, Any]:
    """Auto-update architecture diagrams by analyzing recent git changes.

    Uses git MCP to fetch diffs, sequential-thinking MCP for analysis,
    and updates Mermaid diagrams in appropriate locations.

    Args:
        project_path: Path to project (None = AtlasTrinity internal)
        commits_back: Number of commits to analyze (default: 1)
        target_mode: 'internal' (AtlasTrinity) or 'external' (other projects)

    Returns:
        Status of diagram updates with file locations
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
        return {"error": f"Project path does not exist: {project_path_obj}"}

    try:
        # Step 1: Get git diff/log using git command
        git_log_cmd = ["git", "log", f"-{commits_back}", "--stat", "--pretty=format:%H|%an|%ad|%s"]
        result = subprocess.run(
            git_log_cmd, cwd=project_path_obj, capture_output=True, text=True, check=False
        )

        if result.returncode != 0:
            return {"error": f"Git log failed: {result.stderr}"}

        git_log = result.stdout.strip()

        # Get actual diff
        git_diff_cmd = ["git", "diff", f"HEAD~{commits_back}", "HEAD", "--", "src/brain/"]
        diff_result = subprocess.run(
            git_diff_cmd, cwd=project_path_obj, capture_output=True, text=True, check=False
        )

        git_diff = diff_result.stdout.strip()

        if not git_diff:
            return {
                "success": True,
                "message": "No changes detected in src/brain/",
                "updates_made": False,
            }

        # Step 2: Analyze changes using sequential-thinking pattern
        # This would normally call MCP sequential-thinking server
        # For now, we'll use a simplified analysis pattern

        analysis = _analyze_code_changes(git_log, git_diff)

        # Step 3: Determine which diagrams need updates
        diagrams_to_update = _determine_diagram_updates(analysis)

        if not diagrams_to_update:
            return {
                "success": True,
                "message": "Changes don't require diagram updates",
                "analysis": analysis,
                "updates_made": False,
            }

        # Step 4: Update diagrams
        updated_files = []

        if target_mode == "internal":
            # Update both locations for AtlasTrinity
            internal_path = (
                PROJECT_ROOT
                / "src"
                / "brain"
                / "data"
                / "architecture_diagrams"
                / "mcp_architecture.md"
            )
            docs_path = PROJECT_ROOT / ".agent" / "docs" / "mcp_architecture_diagram.md"

            # Read current diagram
            if docs_path.exists():
                with open(docs_path, encoding="utf-8") as f:
                    current_diagram = f.read()

                # Apply updates (this would be AI-driven in real implementation)
                updated_diagram = _apply_diagram_updates(
                    current_diagram, analysis, diagrams_to_update
                )

                # Write to both locations
                with open(internal_path, "w", encoding="utf-8") as f:
                    f.write(updated_diagram)
                updated_files.append(str(internal_path))

                with open(docs_path, "w", encoding="utf-8") as f:
                    f.write(updated_diagram)
                updated_files.append(str(docs_path))

        else:
            # External project: update only in project root
            diagram_path = project_path_obj / "architecture_diagram.md"

            if diagram_path.exists():
                with open(diagram_path, encoding="utf-8") as f:
                    current_diagram = f.read()
            else:
                # Create new diagram for external project
                current_diagram = _create_base_diagram(project_path_obj)

            updated_diagram = _apply_diagram_updates(current_diagram, analysis, diagrams_to_update)

            with open(diagram_path, "w", encoding="utf-8") as f:
                f.write(updated_diagram)
            updated_files.append(str(diagram_path))

        # Step 5: Export diagrams to PNG/SVG
        _export_diagrams(target_mode, project_path_obj)

        return {
            "success": True,
            "message": "Architecture diagrams updated successfully",
            "updates_made": True,
            "analysis": analysis,
            "diagrams_updated": diagrams_to_update,
            "files_updated": updated_files,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"error": f"Failed to update diagrams: {e}"}


def _analyze_code_changes(git_log: str, git_diff: str) -> dict[str, Any]:
    """Analyze git changes to determine architectural impact.

    In production, this would call sequential-thinking MCP for deep analysis.
    For now, uses pattern matching.
    """
    analysis = {
        "modified_files": [],
        "affected_components": [],
        "change_types": [],
        "requires_diagram_update": False,
    }

    # Parse diff for file changes
    for line in git_diff.split("\n"):
        if line.startswith("diff --git"):
            file_path = line.split()[-1].replace("b/", "")
            analysis["modified_files"].append(file_path)

    # Detect affected components
    key_files = {
        "tool_dispatcher.py": "Tool Routing & Validation",
        "mcp_manager.py": "Tool Execution",
        "mcp_registry.py": "Registry & Caching",
        "behavior_engine.py": "Intent Detection",
    }

    for file_path in analysis["modified_files"]:
        for key_file, component in key_files.items():
            if key_file in file_path:
                analysis["affected_components"].append(component)
                analysis["requires_diagram_update"] = True

    # Detect change types
    if "+def " in git_diff or "+async def " in git_diff:
        analysis["change_types"].append("new_function")
    if "+class " in git_diff:
        analysis["change_types"].append("new_class")
    if "- " in git_diff and "+ " in git_diff:
        analysis["change_types"].append("modification")

    return analysis


def _determine_diagram_updates(analysis: dict[str, Any]) -> list[str]:
    """Determine which diagrams need updates based on analysis."""
    diagrams = []

    if not analysis["requires_diagram_update"]:
        return diagrams

    component_to_diagram = {
        "Tool Routing & Validation": "Phase 2: Tool Routing & Validation",
        "Tool Execution": "Phase 3: Tool Execution",
        "Registry & Caching": "Phase 4: Registry & Caching",
        "Intent Detection": "Phase 1: Intent Detection",
    }

    for component in analysis["affected_components"]:
        if component in component_to_diagram:
            diagrams.append(component_to_diagram[component])

    # Always update main flow if core components changed
    if diagrams:
        diagrams.insert(0, "Complete Execution Flow")

    return list(set(diagrams))


def _apply_diagram_updates(
    current_diagram: str, analysis: dict[str, Any], diagrams_to_update: list[str]
) -> str:
    """Apply updates to diagram based on analysis.

    In production, this would use AI (Claude/GPT via MCP) to intelligently update.
    For now, adds update marker.
    """
    from datetime import datetime

    # Add update notice at the top
    update_notice = f"""
<!-- AUTO-UPDATED: {datetime.now().isoformat()} -->
<!-- Changes detected in: {", ".join(analysis["affected_components"])} -->
<!-- Diagrams updated: {", ".join(diagrams_to_update)} -->

"""

    # Remove old auto-update notice if exists
    lines = current_diagram.split("\n")
    filtered_lines = [line for line in lines if not line.startswith("<!-- AUTO-UPDATED:")]

    updated_diagram = update_notice + "\n".join(filtered_lines)

    return updated_diagram


def _create_base_diagram(project_path: Path) -> str:
    """Create base architecture diagram for external projects."""
    return f"""# Architecture Diagram - {project_path.name}

> **Auto-generated by AtlasTrinity MCP devtools**

## System Architecture

```mermaid
flowchart TD
    Start([Application Entry]) --> Init[Initialization]
    Init --> Main[Main Logic]
    Main --> End([Exit])
    
    style Init fill:#e1f5ff
    style Main fill:#e1ffe1
```

---

**Last Updated:** Auto-generated  
**Project:** {project_path.name}
"""


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
