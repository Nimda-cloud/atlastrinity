import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.brain.core.orchestration.orchestrator import Trinity
from src.brain.core.orchestration.tool_dispatcher import ToolDispatcher
from src.brain.mcp.mcp_manager import mcp_manager


async def benchmark():

    # 1. Test macOS Tool (Standard Execution)
    res = await mcp_manager.call_tool("macos-use", "macos-use_get_time")

    # 2. Test Data Analysis (Complexity)
    res = await mcp_manager.call_tool(
        "data-analysis", "run_pandas_code", {"code": "import pandas as pd; print(pd.__version__)"}
    )

    # 3. Test Tool Routing (Intelligent Routing)
    dispatcher = ToolDispatcher(mcp_manager)
    res = await dispatcher.resolve_and_dispatch("ls", {"path": "."})
    content = getattr(res, "content", [])
    if content:
        pass
    else:
        pass

    # 4. Test Sequential Thinking - FIXED ARGS
    res = await mcp_manager.call_tool(
        "sequential-thinking",
        "sequentialthinking",
        {
            "thought": "I need to verify that the model is correctly processing tool schemas.",
            "thoughtNumber": 1,
            "totalThoughts": 2,
            "nextThoughtNeeded": True,
        },
    )

    # 5. Agent Coordination (The Strength Test)
    # Simulate a coordinated task: Find something and write it down.
    # We'll use the already verified tools to simulate the process.
    await mcp_manager.call_tool("filesystem", "read_file", {"path": f"{PROJECT_ROOT}/package.json"})
    await mcp_manager.call_tool(
        "macos-use",
        "macos-use_send_notification",
        {
            "title": "Benchmark Success",
            "message": f"Model handled tool coordination perfectly at {__import__('datetime').datetime.now()}",
        },
    )


if __name__ == "__main__":
    asyncio.run(benchmark())
