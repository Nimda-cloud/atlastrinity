import asyncio
import os
import sys
from pathlib import Path

sys.path.append(os.getcwd())

from src.brain.mcp_manager import MCPManager


async def test_tool_call():
    manager = MCPManager()
    server_name = "filesystem"
    tool_name = "list_directory"
    args = {"path": str(Path.home() / "Documents/GitHub/atlastrinity")}

    try:
        # Ensure server is connected
        success = await manager.ensure_servers_connected([server_name])
        if not success.get(server_name):
            return

        # Call tool
        result = await manager.call_tool(server_name, tool_name, args)

        if result and not getattr(result, "is_error", False):
            pass
        else:
            pass

    except Exception:
        import traceback

        traceback.print_exc()
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    asyncio.run(test_tool_call())
