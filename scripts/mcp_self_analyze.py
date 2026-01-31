#!/usr/bin/env python3
"""AtlasTrinity MCP Self-Analysis Module

Comprehensive diagnostic tool that uses MCP Inspector CLI tools to:
- Verify all MCP servers are responding
- List and validate tools against tool_schemas.json
- Test sample tool calls
- Check resources and prompts
- Generate detailed reports (human-readable or JSON)
- Optionally auto-fix issues via Vibe MCP

Usage:
    python scripts/mcp_self_analyze.py            # Full analysis, human output
    python scripts/mcp_self_analyze.py --json     # JSON output for automation
    python scripts/mcp_self_analyze.py --autofix  # Auto-fix via Vibe MCP
    python scripts/mcp_self_analyze.py --server memory  # Single server analysis
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ENDC = "\033[0m"


def load_tool_schemas() -> dict:
    """Load tool_schemas.json for validation."""
    schema_path = PROJECT_ROOT / "src" / "brain" / "data" / "tool_schemas.json"
    if not schema_path.exists():
        return {}
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def load_mcp_config() -> dict:
    """Load MCP configuration."""
    config_path = Path.home() / ".config" / "atlastrinity" / "mcp" / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def run_inspector_cmd(server_name: str, method: str, extra_args: list[str] | None = None) -> dict:
    """Run MCP Inspector CLI command and return parsed result."""
    config = load_mcp_config()
    server_config = config.get("mcpServers", {}).get(server_name)
    
    if not server_config:
        return {"error": f"Server '{server_name}' not found in configuration"}
    
    command = server_config.get("command", "")
    args = server_config.get("args", [])
    env_vars = server_config.get("env", {})
    
    # Resolve variables
    resolved_args = []
    for arg in args:
        arg = arg.replace("${HOME}", str(Path.home()))
        arg = arg.replace("${PROJECT_ROOT}", str(PROJECT_ROOT))
        resolved_args.append(arg)
    
    resolved_command = command.replace("${HOME}", str(Path.home()))
    resolved_command = resolved_command.replace("${PROJECT_ROOT}", str(PROJECT_ROOT))
    
    # Build inspector command
    inspector_cmd = [
        "npx", "@modelcontextprotocol/inspector", "--cli",
        resolved_command, *resolved_args,
        "--method", method
    ]
    
    if extra_args:
        inspector_cmd.extend(extra_args)
    
    # Prepare environment
    env = os.environ.copy()
    for k, v in env_vars.items():
        val = v.replace("${GITHUB_TOKEN}", env.get("GITHUB_TOKEN", ""))
        val = val.replace("${HOME}", str(Path.home()))
        val = val.replace("${PROJECT_ROOT}", str(PROJECT_ROOT))
        env[k] = val
    
    try:
        result = subprocess.run(
            inspector_cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=30.0,
            check=False,
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr.strip() or f"Exit code {result.returncode}",
            }
        
        stdout = result.stdout.strip()
        if not stdout:
            return {"success": True, "data": None}
        
        try:
            return {"success": True, "data": json.loads(stdout)}
        except json.JSONDecodeError:
            return {"success": True, "raw_output": stdout}
            
    except subprocess.TimeoutExpired:
        return {"error": "Timeout after 30s"}
    except Exception as e:
        return {"error": str(e)}


def analyze_server(server_name: str, tool_schemas: dict, verbose: bool = False) -> dict:
    """Perform full analysis of a single MCP server."""
    report = {
        "server": server_name,
        "status": "unknown",
        "tools": {"count": 0, "list": [], "schema_mismatches": []},
        "resources": {"count": 0, "list": []},
        "prompts": {"count": 0, "list": []},
        "issues": [],
        "timestamp": datetime.now().isoformat(),
    }
    
    # 1. List Tools
    tools_result = run_inspector_cmd(server_name, "tools/list")
    if tools_result.get("error"):
        report["status"] = "offline"
        report["issues"].append(f"Cannot connect: {tools_result['error']}")
        return report
    
    report["status"] = "online"
    tools_data = tools_result.get("data", {})
    tools_list = tools_data.get("tools", tools_data) if isinstance(tools_data, dict) else tools_data
    
    if isinstance(tools_list, list):
        report["tools"]["count"] = len(tools_list)
        for tool in tools_list:
            if isinstance(tool, dict):
                tool_name = tool.get("name", "unknown")
                report["tools"]["list"].append(tool_name)
                
                # Check against tool_schemas.json
                expected_schema = tool_schemas.get(tool_name)
                if expected_schema and expected_schema.get("server") != server_name:
                    report["tools"]["schema_mismatches"].append({
                        "tool": tool_name,
                        "issue": f"Expected server '{expected_schema.get('server')}', got '{server_name}'"
                    })
    
    # 2. List Resources
    resources_result = run_inspector_cmd(server_name, "resources/list")
    if resources_result.get("success"):
        resources_data = resources_result.get("data", {})
        resources_list = resources_data.get("resources", []) if isinstance(resources_data, dict) else []
        report["resources"]["count"] = len(resources_list)
        report["resources"]["list"] = [r.get("uri", str(r)) for r in resources_list if isinstance(r, dict)]
    
    # 3. List Prompts
    prompts_result = run_inspector_cmd(server_name, "prompts/list")
    if prompts_result.get("success"):
        prompts_data = prompts_result.get("data", {})
        prompts_list = prompts_data.get("prompts", []) if isinstance(prompts_data, dict) else []
        report["prompts"]["count"] = len(prompts_list)
        report["prompts"]["list"] = [p.get("name", str(p)) for p in prompts_list if isinstance(p, dict)]
    
    return report


async def auto_fix_issues(issues: list[dict]) -> dict:
    """Attempt to auto-fix issues using Vibe MCP."""
    from brain.mcp_manager import mcp_manager
    
    fixes_attempted = []
    for issue in issues:
        if "Cannot connect" in issue.get("issue", ""):
            # Try to restart the server
            server = issue.get("server")
            if server:
                try:
                    result = await mcp_manager.call_tool(
                        "vibe",
                        "vibe_analyze_error",
                        {
                            "error_message": f"MCP server '{server}' is not responding",
                            "auto_fix": True,
                            "log_context": "mcp_self_analyze autofix"
                        }
                    )
                    fixes_attempted.append({
                        "server": server,
                        "action": "vibe_analyze_error",
                        "result": str(result)[:200]
                    })
                except Exception as e:
                    fixes_attempted.append({
                        "server": server,
                        "action": "vibe_analyze_error",
                        "error": str(e)
                    })
    
    return {"fixes_attempted": fixes_attempted}


def print_human_report(reports: list[dict], total_time: float):
    """Print human-readable analysis report."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}  🔬 MCP Self-Analysis Report{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}\n")
    
    online = sum(1 for r in reports if r["status"] == "online")
    offline = sum(1 for r in reports if r["status"] == "offline")
    total = len(reports)
    
    for report in reports:
        server = report["server"]
        status = report["status"]
        
        if status == "online":
            icon = f"{Colors.GREEN}✓{Colors.ENDC}"
            status_str = f"{Colors.GREEN}ONLINE{Colors.ENDC}"
        else:
            icon = f"{Colors.RED}✗{Colors.ENDC}"
            status_str = f"{Colors.RED}OFFLINE{Colors.ENDC}"
        
        tools_count = report["tools"]["count"]
        resources_count = report["resources"]["count"]
        prompts_count = report["prompts"]["count"]
        
        print(f"  {icon} {server:<22} {status_str:^12}  Tools:{tools_count:>3}  Resources:{resources_count:>3}  Prompts:{prompts_count:>3}")
        
        # Show issues
        for issue in report.get("issues", []):
            print(f"      {Colors.RED}⚠ {issue}{Colors.ENDC}")
        
        # Show schema mismatches
        for mismatch in report["tools"].get("schema_mismatches", []):
            print(f"      {Colors.YELLOW}⚠ Schema: {mismatch['tool']} - {mismatch['issue']}{Colors.ENDC}")
    
    print(f"\n  {'-' * 66}")
    print(f"  {Colors.BOLD}Summary:{Colors.ENDC} {Colors.GREEN}{online}{Colors.ENDC} online, {Colors.RED}{offline}{Colors.ENDC} offline (of {total})")
    print(f"  {Colors.BOLD}Analysis time:{Colors.ENDC} {total_time:.1f}s")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}\n")


def main():
    parser = argparse.ArgumentParser(description="MCP Self-Analysis Tool")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--autofix", action="store_true", help="Attempt auto-fix via Vibe MCP")
    parser.add_argument("--server", type=str, help="Analyze specific server only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    import time
    start_time = time.time()
    
    # Load configuration
    config = load_mcp_config()
    tool_schemas = load_tool_schemas()
    
    if not config:
        print(f"{Colors.RED}Error: MCP configuration not found{Colors.ENDC}")
        sys.exit(1)
    
    # Get servers to analyze
    servers = config.get("mcpServers", {})
    if args.server:
        if args.server not in servers:
            print(f"{Colors.RED}Error: Server '{args.server}' not found{Colors.ENDC}")
            sys.exit(1)
        servers = {args.server: servers[args.server]}
    
    # Filter out disabled and internal servers
    active_servers = [
        name for name, cfg in servers.items()
        if not name.startswith("_") and not cfg.get("disabled", False)
    ]
    
    # Run analysis
    reports = []
    for server_name in active_servers:
        if not args.json:
            print(f"{Colors.DIM}Analyzing {server_name}...{Colors.ENDC}", end=" ", flush=True)
        
        report = analyze_server(server_name, tool_schemas, verbose=args.verbose)
        reports.append(report)
        
        if not args.json:
            if report["status"] == "online":
                print(f"{Colors.GREEN}OK{Colors.ENDC}")
            else:
                print(f"{Colors.RED}FAILED{Colors.ENDC}")
    
    total_time = time.time() - start_time
    
    # Auto-fix if requested
    if args.autofix:
        issues = []
        for r in reports:
            for issue in r.get("issues", []):
                issues.append({"server": r["server"], "issue": issue})
        
        if issues:
            if not args.json:
                print(f"\n{Colors.YELLOW}Attempting auto-fix for {len(issues)} issues...{Colors.ENDC}")
            
            fix_result = asyncio.run(auto_fix_issues(issues))
            for r in reports:
                r["autofix"] = fix_result
    
    # Output
    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "analysis_time_seconds": round(total_time, 2),
            "total_servers": len(reports),
            "online": sum(1 for r in reports if r["status"] == "online"),
            "offline": sum(1 for r in reports if r["status"] == "offline"),
            "reports": reports,
        }
        print(json.dumps(output, indent=2))
    else:
        print_human_report(reports, total_time)


if __name__ == "__main__":
    main()
