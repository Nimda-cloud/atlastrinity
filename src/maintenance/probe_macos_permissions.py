import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.getcwd()))
from src.brain.mcp_manager import mcp_manager


async def probe():
    try:
        # Force a connection even if lazy loaded
        session = await mcp_manager.get_session("macos-use")
        if not session:
            return

        tools = await mcp_manager.list_tools("macos-use")

        for _ in tools:
            pass

    except Exception:
        pass

    await mcp_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(probe())
