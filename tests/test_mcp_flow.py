import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.getcwd()))

from src.brain.mcp.mcp_manager import mcp_manager


async def test_flow():
    print("--- 1. Testing Initialization ---")
    # Initialize basic logging
    import logging

    logging.basicConfig(level=logging.INFO)

    print("--- 2. Testing Catalog Generation (with Tool Names) ---")
    # This triggers list_tools for all enabled servers
    catalog = ""
    try:
        catalog = await mcp_manager.get_mcp_catalog()
        print("\nCatalog Output Preview:\n" + "=" * 40)
        print(catalog)
        print("=" * 40 + "\n")

        if "(Tools:" in catalog or "Tools: " in catalog:
            print("✅ SUCCESS: Tool names found in catalog.")
        else:
            print("❌ FAILURE: Tool names NOT found in catalog.")
    except Exception as e:
        print(f"❌ CRITICAL FAILURE during catalog generation: {e}")
        import traceback

        traceback.print_exc()

    print("\n--- 3. Testing Execution (Filesystem) ---")
    try:
        # Try listing the current directory
        cwd = os.getcwd()
        print(f"Listing directory: {cwd}")

        # Check if filesystem server is active in catalog
        if "filesystem" in catalog:
            result = await mcp_manager.call_tool("filesystem", "list_directory", {"path": cwd})
            print(f"Execution Result: {result}")

            # The result from mcp python sdk is an object, usually CallToolResult
            if hasattr(result, "content"):
                print("✅ SUCCESS: Execution returned content.")
            else:
                print("⚠️ WARNING: content not found in result object.")
        else:
            print("⚠️ SKIPPING: Filesystem server not found in catalog.")

    except Exception as e:
        print(f"❌ FAILURE: Execution failed: {e}")

        traceback.print_exc()

    print("\n--- Cleanup ---")
    await mcp_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(test_flow())
