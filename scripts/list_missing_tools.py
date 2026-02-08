import asyncio
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from brain.mcp_manager import mcp_manager


async def get_tools():
    for server in ["github", "context7"]:
        print(f"--- Server: {server} ---")
        try:
            tools = await mcp_manager.list_tools(server)
            tool_names = [t.name for t in tools]
            print(f"Tools: {tool_names}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(get_tools())
