import asyncio
import logging
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.brain.mcp_manager import mcp_manager
from src.brain.memory import long_term_memory

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_memory")


async def verify():
    print("--- Verifying Memory System ---")

    # 1. Check Internal LongTermMemory (ChromaDB)
    print(f"LongTermMemory Available: {long_term_memory.available}")
    if long_term_memory.available:
        stats = long_term_memory.get_stats()
        print(f"ChromaDB Stats: {stats}")

    # 2. Check MCP Memory Server Connection
    print("\nChecking MCP 'memory' server...")
    try:
        # MCP Manager initializes config on construction

        session = await mcp_manager.get_session("memory")
        if session:
            print("Successfully connected to 'memory' MCP server.")

            # Try a simple tool call
            print("Testing tool call 'get_memory_stats' (or similar)...")
            # The memory server probably exposes tools. Let's list them if possible or try a benign one.
            # Usually 'memory' server has 'read_graph', 'search_nodes' etc.
            # Let's try searching for "Atlas"

            res = await mcp_manager.call_tool("memory", "search_nodes", {"query": "Atlas"})
            print(f"Search Result: {str(res)[:200]}...")

        else:
            print("Failed to get session for 'memory' server.")

    except Exception as e:
        print(f"MCP Check Failed: {e}")


if __name__ == "__main__":
    asyncio.run(verify())
