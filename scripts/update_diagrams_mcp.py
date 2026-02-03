#!/usr/bin/env python3
"""
Wrapper script to call devtools_update_architecture_diagrams via MCP.
This is used by npm scripts to trigger automatic diagram updates.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from brain.mcp_manager import MCPManager


async def main():
    """Call devtools MCP to update architecture diagrams."""
    manager = MCPManager()

    try:
        # Call the tool
        result = await manager.call_tool(
            server_name="devtools",
            tool_name="devtools_update_architecture_diagrams",
            arguments={
                "project_path": None,  # None = AtlasTrinity internal
                "commits_back": 1,
                "target_mode": "internal",
            },
        )

        if hasattr(result, "structuredContent") and result.structuredContent:
            res_data = result.structuredContent
        elif isinstance(result, dict):
            res_data = result
        elif hasattr(result, "content") and result.content:
            # Try to parse text content as JSON if it's a list of TextContent
            import json
            try:
                res_data = json.loads(result.content[0].text)
            except (IndexError, AttributeError, json.JSONDecodeError):
                print(f"❌ Unexpected result format: {result}")
                sys.exit(1)
        else:
            print(f"❌ Unexpected result: {result}")
            sys.exit(1)

        if res_data.get("success"):
            print("✅ Architecture diagrams updated successfully")
            if res_data.get("files_updated"):
                print("📝 Updated files:")
                for file_path in res_data["files_updated"]:
                    print(f"   - {file_path}")
            if not res_data.get("updates_made"):
                print("ℹ️  No changes detected requiring diagram updates")
        else:
            error = res_data.get("error", "Unknown error")
            print(f"❌ Failed to update diagrams: {error}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
