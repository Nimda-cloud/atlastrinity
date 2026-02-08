import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.getcwd()))
from src.brain.mcp_manager import mcp_manager


async def probe():
    print("--- Probing macos-use Server ---")
    try:
        # Force a connection even if lazy loaded
        session = await mcp_manager.get_session("macos-use")
        if not session:
            print("❌ Could not connect to 'macos-use'. Check if binary exists.")
            return

        print("✅ Connected to 'macos-use'. Fetching tools...")
        tools = await mcp_manager.list_tools("macos-use")

        print(f"\nFound {len(tools)} tools:")
        for t in tools:
            print(f"- {t.name}: {t.description}")

    except Exception as e:
        print(f"❌ Error probing macos-use: {e}")

    print("\n--- Cleanup ---")
    await mcp_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(probe())
