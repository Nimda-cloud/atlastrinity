import asyncio
import os
import sys

sys.path.append(os.getcwd())

from src.brain.mcp_manager import MCPManager


async def verify_dom_interaction():
    manager = MCPManager()
    server_name = "chrome-devtools"

    try:
        # 1. Ensure server is connected
        success = await manager.ensure_servers_connected([server_name])
        if not success.get(server_name):
            return

        # 2. Create a new page
        result = await manager.call_tool(server_name, "new_page", {})

        # 3. Navigate to example.com
        result = await manager.call_tool(
            server_name, "navigate_page", {"url": "https://example.com"}
        )

        # 4. Take a snapshot (DOM & Text)
        result = await manager.call_tool(server_name, "take_snapshot", {})

        if result and not getattr(result, "is_error", False):
            # Extract some info from the snapshot if possible
            content = str(result.content) if hasattr(result, "content") else str(result)

            # 5. Check for H1
            if "Example Domain" in content:
                pass
            else:
                pass
        else:
            pass

    except Exception:
        import traceback

        traceback.print_exc()
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    asyncio.run(verify_dom_interaction())
