import asyncio
import os
import sys

# Fix path to include src
sys.path.append(os.getcwd())

from src.brain.mcp_manager import MCPManager


async def verify_dom_interaction():
    manager = MCPManager()
    server_name = "chrome-devtools"

    print(f"--- Verifying DOM Interaction: {server_name} ---")

    try:
        # 1. Ensure server is connected
        print(f"Connecting to {server_name}...")
        success = await manager.ensure_servers_connected([server_name])
        if not success.get(server_name):
            print(f"❌ Failed to connect to {server_name}")
            return

        # 2. Create a new page
        print("Creating a new page...")
        result = await manager.call_tool(server_name, "new_page", {})
        print(f"New page result: {result}")

        # 3. Navigate to example.com
        print("Navigating to https://example.com...")
        result = await manager.call_tool(
            server_name, "navigate_page", {"url": "https://example.com"}
        )
        print(f"Navigation result: {result}")

        # 4. Take a snapshot (DOM & Text)
        print("Taking a snapshot of the DOM...")
        result = await manager.call_tool(server_name, "take_snapshot", {})

        if result and not getattr(result, "is_error", False):
            # Extract some info from the snapshot if possible
            content = str(result.content) if hasattr(result, "content") else str(result)
            print("\n✅ Success! Snapshot retrieved.")
            print(f"Content preview: {content[:500]}...")

            # 5. Check for H1
            if "Example Domain" in content:
                print("\n✅ Verified: Found 'Example Domain' in the DOM snapshot.")
            else:
                print(
                    "\n⚠️ Warning: 'Example Domain' not found in content, but snapshot was successful."
                )
        else:
            print("\n❌ Failure. Snapshot tool returned error.")

    except Exception as e:
        print(f"\n❌ Exception occurred: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    asyncio.run(verify_dom_interaction())
