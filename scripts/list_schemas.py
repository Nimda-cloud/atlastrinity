import asyncio
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.getcwd(), "src"))
sys.path.insert(0, PROJECT_ROOT)

from brain.mcp_manager import mcp_manager


async def get_schemas():
    for server in ["vibe"]:
        print(f"=== SCHEMA FOR {server} ===")
        tools = await mcp_manager.list_tools(server)
        result = []
        for t in tools:
            schema = {
                "name": t.name,
                "description": getattr(t, "description", ""),
                "inputSchema": getattr(t, "inputSchema", {}),
            }
            result.append(schema)
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(get_schemas())
