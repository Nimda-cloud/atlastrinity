import asyncio
import json
import os
import sys
from typing import Dict, Any, List

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.mcp_manager import mcp_manager
from src.brain.config_loader import config

async def verify_server(server_name: str, server_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Connects to a server and verifies its tool capabilities.
    Returns a report dictionary.
    """
    report = {
        "server": server_name,
        "status": "UNKNOWN",
        "tool_count": 0,
        "tools": [],
        "errors": [],
        "tier": server_config.get("tier", "unknown"),
        "disabled": server_config.get("disabled", False)
    }

    # Skip if disabled (unless we want to force-check, but usually disabled means not runnable)
    # The user asked to check ALL servers. If disabled, we can't connect usually unless we force-enable.
    # For this report, we will try to connect even if disabled by temporarily overriding?
    # mcp_manager checks config. IF we want to check disabled ones, we might need to trick it 
    # OR better, just report them as Disabled.
    # However, user said "Review... for all servers". 
    # mcp_manager.list_tools() checks valid session. get_session() checks config.
    
    if report["disabled"]:
        report["status"] = "DISABLED"
        return report

    try:
        # Force connection / list_tools
        # We use mcp_manager.list_tools which handles session creation
        tools = await mcp_manager.list_tools(server_name)
        
        report["status"] = "OK"
        report["tool_count"] = len(tools)
        
        for t in tools:
            t_name = getattr(t, "name", str(t))
            t_desc = getattr(t, "description", None)
            t_schema = getattr(t, "inputSchema", None)
            
            tool_info = {
                "name": t_name,
                "has_description": bool(t_desc),
                "has_schema": bool(t_schema),
                "description_preview": (t_desc or "")[:50] + "..." if t_desc else "N/A",
                "schema_valid": isinstance(t_schema, dict) and "properties" in t_schema if t_schema else False
            }
            report["tools"].append(tool_info)
            
            if not t_desc:
                report["errors"].append(f"Tool '{t_name}' missing description")
            if not t_schema:
                report["errors"].append(f"Tool '{t_name}' missing inputSchema")
                
    except Exception as e:
        report["status"] = "ERROR"
        report["errors"].append(str(e))
        
    return report

async def main():
    print("Starting MCP Verification...")
    
    # 1. Get List Component
    raw_config = mcp_manager.config.get("mcpServers", {})
    servers_to_check = []
    
    for key, value in raw_config.items():
        if key.startswith("_"):
            continue
        servers_to_check.append((key, value))
        
    print(f"Found {len(servers_to_check)} servers in config.")
    
    reports = []
    results = await asyncio.gather(*[verify_server(name, cfg) for name, cfg in servers_to_check])
    
    # Generate Markdown Report
    md_report = "# MCP Server Review\n\n"
    md_report += f"Generated at: {json.dumps(str(asyncio.get_event_loop().time()))}\n\n"
    
    for res in results:
        icon = "✅" if res["status"] == "OK" else "❌"
        if res["status"] == "DISABLED": icon = "⚪️"
        
        md_report += f"## {icon} {res['server']} (Tier {res['tier']})\n"
        md_report += f"- **Status**: {res['status']}\n"
        md_report += f"- **Tools**: {res['tool_count']}\n"
        
        if res["errors"]:
            md_report += f"- **Issues**: {len(res['errors'])}\n"
            for err in res["errors"]:
                md_report += f"  - ⚠️ {err}\n"
        
        if res["tools"]:
            md_report += "\n| Tool | Desc? | Schema? | Preview |\n|---|---|---|---|\n"
            for t in res["tools"]:
                d = "Yes" if t["has_description"] else "**NO**"
                s = "Yes" if t["has_schema"] else "**NO**"
                md_report += f"| {t['name']} | {d} | {s} | {t['description_preview']} |\n"
        
        md_report += "\n"

    print(md_report)
    
    # Save to file
    with open("mcp_review_report.md", "w") as f:
        f.write(md_report)

if __name__ == "__main__":
    asyncio.run(main())
