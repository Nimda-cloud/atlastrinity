import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.brain.mcp.mcp_manager import mcp_manager


async def get_tools():
    for server in ["github", "context7"]:
        try:
            tools = await mcp_manager.list_tools(server)
            [t.name for t in tools]
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(get_tools())
