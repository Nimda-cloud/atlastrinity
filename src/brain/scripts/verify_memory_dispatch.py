import asyncio
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.brain.mcp.mcp_manager import mcp_manager

# Setup logging
logging.basicConfig(level=logging.INFO, encoding="utf-8")
logger = logging.getLogger("verify_dispatch")


async def verify():
    print("--- Verifying Memory Dispatcher Fix ---")

    try:
        # await mcp_manager.initialize() - Not needed/doesn't exist

        print("\nTesting 'memory' generic call dispatch...")

        # This simulates the problematic call found in logs:
        # [DISPATCHER] Calling memory with ['query', 'limit', 'step_id']

        # We explicitly call "memory" tool via dispatch_tool to test routing.
        # This simulates an agent calling dispatch_tool("memory", args).

        res = await mcp_manager.dispatch_tool(
            "memory",
            {"query": "Atlas Test Dispatch", "limit": 1, "step_id": "test_123"},
            explicit_server="memory",
        )

        print(f"Result Type: {type(res)}")

        # Check if result looks like search results
        res_str = str(res)
        if (
            "results" in res_str
            or "entities" in res_str
            or "Atlas" in res_str
            or isinstance(res, list | dict)
        ):
            print("SUCCESS: Dispatcher handled 'memory' call!")
            print(f"Result Preview: {res_str[:200]}")
        else:
            print(f"WARNING: Unexpected result format: {res_str[:200]}")

    except Exception as e:
        print(f"FAILURE: Exception occurred: {e}")
        # If it says "Tool 'memory' not listed", then the fix failed.


if __name__ == "__main__":
    asyncio.run(verify())
