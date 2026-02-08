import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


async def test_servers():
    import logging

    from src.brain.mcp_manager import mcp_manager

    # Set logger to info to see results
    logging.getLogger("brain").setLevel(logging.INFO)

    print("\n=== MCP Server Connectivity Test ===\n")

    servers = mcp_manager.get_available_servers()
    results = {}

    # Test a representative sample of different types
    test_targets = ["macos-use", "filesystem", "vibe", "devtools", "googlemaps"]
    # Filter only configured ones
    test_targets = [s for s in test_targets if s in servers]

    for server_name in test_targets:
        print(f"Testing {server_name}...")
        try:
            session = await mcp_manager.get_session(server_name)
            if session:
                tools = await session.list_tools()
                print(f"✅ {server_name}: Connected. Found {len(tools.tools)} tools.")
                results[server_name] = True
            else:
                print(f"❌ {server_name}: Failed to get session.")
                results[server_name] = False
        except Exception as e:
            print(f"❌ {server_name}: Error - {e}")
            results[server_name] = False

    print("\n=== Summary ===\n")
    all_ok = all(results.values())
    for s, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"{s}: {status}")

    if all_ok:
        print("\nAll tested servers are working correctly with 'stdio' transport.")
    else:
        print("\nSome servers failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_servers())
