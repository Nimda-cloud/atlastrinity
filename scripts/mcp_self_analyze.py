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
        "npx",
        "@modelcontextprotocol/inspector",
        "--cli",
        resolved_command,
        *resolved_args,
        "--method",
        method,
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
                    report["tools"]["schema_mismatches"].append(
                        {
                            "tool": tool_name,
                            "issue": f"Expected server '{expected_schema.get('server')}', got '{server_name}'",
                        }
                    )

    # 2. List Resources
    resources_result = run_inspector_cmd(server_name, "resources/list")
    if resources_result.get("success"):
        resources_data = resources_result.get("data", {})
        resources_list = (
            resources_data.get("resources", []) if isinstance(resources_data, dict) else []
        )
        report["resources"]["count"] = len(resources_list)
        report["resources"]["list"] = [
            r.get("uri", str(r)) for r in resources_list if isinstance(r, dict)
        ]

    # 3. List Prompts
    prompts_result = run_inspector_cmd(server_name, "prompts/list")
    if prompts_result.get("success"):
        prompts_data = prompts_result.get("data", {})
        prompts_list = prompts_data.get("prompts", []) if isinstance(prompts_data, dict) else []
        report["prompts"]["count"] = len(prompts_list)
        report["prompts"]["list"] = [
            p.get("name", str(p)) for p in prompts_list if isinstance(p, dict)
        ]

    return report


async def live_verify_tool(
    server_name: str,
    tool_name: str,
    tool_schema: dict,
    tool_description: str,
) -> dict:
    """Use LLM to generate realistic arguments and test the tool.

    This is the 'живе тестування' - the LLM reasons about what arguments
    to use, executes the tool, and analyzes whether the result is correct.
    """
    from providers.copilot import CopilotLLM

    result = {
        "tool": tool_name,
        "status": "unknown",
        "llm_reasoning": "",
        "generated_args": {},
        "tool_output": None,
        "llm_verdict": "",
    }

    # Build prompt for LLM to generate test arguments
    schema_json = json.dumps(tool_schema, indent=2, ensure_ascii=False)

    generate_prompt = f"""You are testing MCP tool '{tool_name}' on server '{server_name}'.

Tool description: {tool_description}

Tool input schema:
{schema_json}

Your task:
1. Generate REALISTIC test arguments that will work on a macOS system.
2. Use safe, read-only values where possible (e.g., existing paths like ~/.zshrc or /tmp).
3. Return ONLY valid JSON object with the arguments. No explanation.

Example for read_file: {{"path": "~/.zshrc"}}
Example for list_directory: {{"path": "/tmp"}}

Generate arguments for '{tool_name}':"""

    try:
        llm = CopilotLLM(model_name="gpt-4.1")

        # Step 1: Generate arguments
        gen_response = await llm.ainvoke(generate_prompt)
        gen_text = gen_response.content if hasattr(gen_response, "content") else str(gen_response)

        result["llm_reasoning"] = f"Generated args: {str(gen_text)[:200]}"

        # Parse generated arguments
        try:
            # Clean up response - extract JSON
            if isinstance(gen_text, list):
                gen_text = gen_text[0] if gen_text else ""
            gen_text = str(gen_text).strip()
            if gen_text.startswith("```"):
                gen_text = gen_text.split("```")[1]
                if gen_text.startswith("json"):
                    gen_text = gen_text[4:]
            generated_args = json.loads(gen_text.strip())
            result["generated_args"] = generated_args
        except json.JSONDecodeError:
            result["status"] = "parse_error"
            result["llm_verdict"] = f"Could not parse LLM response as JSON: {gen_text[:100]}"
            return result

        # Step 2: Call the tool via inspector
        extra_args = ["--tool-name", tool_name]
        for key, value in generated_args.items():
            if isinstance(value, dict | list):
                extra_args.extend(["--tool-arg", f"{key}={json.dumps(value)}"])
            else:
                extra_args.extend(["--tool-arg", f"{key}={value}"])

        call_result = run_inspector_cmd(server_name, "tools/call", extra_args)
        result["tool_output"] = call_result

        if call_result.get("error"):
            result["status"] = "call_error"
            result["llm_verdict"] = f"Tool call failed: {call_result['error']}"
            return result

        # Step 3: LLM analyzes if result is valid
        tool_output_str = json.dumps(call_result, indent=2, ensure_ascii=False)[:1000]

        analyze_prompt = f"""You tested MCP tool '{tool_name}' with args: {json.dumps(generated_args)}

Tool output:
{tool_output_str}

Analyze:
1. Did the tool execute successfully (no errors)?
2. Is the output reasonable for the given arguments?
3. Any warnings or issues?

Respond with ONE word: PASS or FAIL, followed by a brief explanation (max 50 words)."""

        analyze_response = await llm.ainvoke(analyze_prompt)
        verdict = (
            analyze_response.content
            if hasattr(analyze_response, "content")
            else str(analyze_response)
        )

        if isinstance(verdict, list):
            verdict = verdict[0] if verdict else ""
        verdict = str(verdict)

        result["llm_verdict"] = verdict.strip()
        result["status"] = "pass" if verdict.strip().upper().startswith("PASS") else "fail"

        return result

    except Exception as e:
        result["status"] = "exception"
        result["llm_verdict"] = f"Exception during live test: {str(e)[:100]}"
        return result


async def live_verify_server(server_name: str, max_tools: int = 5) -> dict:
    """Perform LLM-driven live verification of a server's tools.

    Args:
        server_name: Name of the MCP server to test
        max_tools: Maximum number of tools to test (to limit API calls)

    Returns:
        Dict with server name, tool results, and summary
    """
    report = {
        "server": server_name,
        "mode": "live_verification",
        "tools_tested": 0,
        "passed": 0,
        "failed": 0,
        "results": [],
        "timestamp": datetime.now().isoformat(),
    }

    # Get tools list
    tools_result = run_inspector_cmd(server_name, "tools/list")
    if tools_result.get("error"):
        report["error"] = tools_result["error"]
        return report

    tools_data = tools_result.get("data", {})
    tools_list = tools_data.get("tools", tools_data) if isinstance(tools_data, dict) else tools_data

    if not isinstance(tools_list, list):
        report["error"] = "Could not parse tools list"
        return report

    # Filter to read-only tools for safety
    safe_tools = []
    for tool in tools_list:
        if isinstance(tool, dict):
            annotations = tool.get("annotations", {})
            # Prefer read-only tools
            if annotations.get("readOnlyHint", False):
                safe_tools.insert(0, tool)
            else:
                safe_tools.append(tool)

    # Test up to max_tools
    tools_to_test = safe_tools[:max_tools]

    for tool in tools_to_test:
        tool_name = tool.get("name", "unknown")
        tool_desc = tool.get("description", "")
        tool_schema = tool.get("inputSchema", {})

        print(f"    {Colors.DIM}Testing {tool_name}...{Colors.ENDC}", end=" ", flush=True)

        test_result = await live_verify_tool(server_name, tool_name, tool_schema, tool_desc)
        report["results"].append(test_result)
        report["tools_tested"] += 1

        if test_result["status"] == "pass":
            report["passed"] += 1
            print(f"{Colors.GREEN}PASS{Colors.ENDC}")
        else:
            report["failed"] += 1
            print(f"{Colors.RED}FAIL{Colors.ENDC} - {test_result['llm_verdict'][:50]}")

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
                            "log_context": "mcp_self_analyze autofix",
                        },
                    )
                    fixes_attempted.append(
                        {
                            "server": server,
                            "action": "vibe_analyze_error",
                            "result": str(result)[:200],
                        }
                    )
                except Exception as e:
                    fixes_attempted.append(
                        {"server": server, "action": "vibe_analyze_error", "error": str(e)}
                    )

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

        print(
            f"  {icon} {server:<22} {status_str:^12}  Tools:{tools_count:>3}  Resources:{resources_count:>3}  Prompts:{prompts_count:>3}"
        )

        # Show issues
        for issue in report.get("issues", []):
            print(f"      {Colors.RED}⚠ {issue}{Colors.ENDC}")

        # Show schema mismatches
        for mismatch in report["tools"].get("schema_mismatches", []):
            print(
                f"      {Colors.YELLOW}⚠ Schema: {mismatch['tool']} - {mismatch['issue']}{Colors.ENDC}"
            )

    print(f"\n  {'-' * 66}")
    print(
        f"  {Colors.BOLD}Summary:{Colors.ENDC} {Colors.GREEN}{online}{Colors.ENDC} online, {Colors.RED}{offline}{Colors.ENDC} offline (of {total})"
    )
    print(f"  {Colors.BOLD}Analysis time:{Colors.ENDC} {total_time:.1f}s")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}\n")


def print_live_report(reports: list[dict], total_time: float):
    """Print human-readable live verification report."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}  🧪 MCP Live Verification Report (LLM-driven){Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}\n")

    total_passed = sum(r.get("passed", 0) for r in reports)
    total_failed = sum(r.get("failed", 0) for r in reports)
    total_tested = sum(r.get("tools_tested", 0) for r in reports)

    for report in reports:
        server = report["server"]
        passed = report.get("passed", 0)
        failed = report.get("failed", 0)
        tested = report.get("tools_tested", 0)

        if failed == 0 and tested > 0:
            icon = f"{Colors.GREEN}✓{Colors.ENDC}"
        elif passed > failed:
            icon = f"{Colors.YELLOW}⚠{Colors.ENDC}"
        else:
            icon = f"{Colors.RED}✗{Colors.ENDC}"

        print(
            f"  {icon} {server:<22} Tested:{tested:>3}  {Colors.GREEN}Pass:{passed}{Colors.ENDC}  {Colors.RED}Fail:{failed}{Colors.ENDC}"
        )

        # Show individual results
        for result in report.get("results", []):
            tool = result.get("tool", "?")
            status = result.get("status", "?")
            verdict = result.get("llm_verdict", "")[:60]

            if status == "pass":
                print(f"      {Colors.GREEN}✓ {tool}{Colors.ENDC}")
            else:
                print(f"      {Colors.RED}✗ {tool}: {verdict}{Colors.ENDC}")

    print(f"\n  {'-' * 66}")
    print(
        f"  {Colors.BOLD}Total:{Colors.ENDC} {total_tested} tools tested, {Colors.GREEN}{total_passed} passed{Colors.ENDC}, {Colors.RED}{total_failed} failed{Colors.ENDC}"
    )
    print(f"  {Colors.BOLD}Analysis time:{Colors.ENDC} {total_time:.1f}s")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}\n")


def main():
    parser = argparse.ArgumentParser(description="MCP Self-Analysis Tool")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--autofix", action="store_true", help="Attempt auto-fix via Vibe MCP")
    parser.add_argument("--server", type=str, help="Analyze specific server only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--live",
        action="store_true",
        help="LLM-driven live verification (tests each tool with generated args)",
    )
    parser.add_argument(
        "--max-tools",
        type=int,
        default=5,
        help="Max tools to test per server in --live mode (default: 5)",
    )
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
        name
        for name, cfg in servers.items()
        if not name.startswith("_") and not cfg.get("disabled", False)
    ]

    # Live verification mode
    if args.live:
        print(
            f"{Colors.BOLD}{Colors.CYAN}🧪 Starting LLM-driven live verification...{Colors.ENDC}\n"
        )

        async def run_live():
            reports = []
            for server_name in active_servers:
                print(f"{Colors.BOLD}▶ {server_name}{Colors.ENDC}")
                report = await live_verify_server(server_name, max_tools=args.max_tools)
                reports.append(report)
            return reports

        reports = asyncio.run(run_live())
        total_time = time.time() - start_time

        if args.json:
            output = {
                "mode": "live_verification",
                "timestamp": datetime.now().isoformat(),
                "analysis_time_seconds": round(total_time, 2),
                "total_servers": len(reports),
                "total_passed": sum(r.get("passed", 0) for r in reports),
                "total_failed": sum(r.get("failed", 0) for r in reports),
                "reports": reports,
            }
            print(json.dumps(output, indent=2))
        else:
            print_live_report(reports, total_time)

        return

    # Standard analysis mode
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
                print(
                    f"\n{Colors.YELLOW}Attempting auto-fix for {len(issues)} issues...{Colors.ENDC}"
                )

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
