
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from src.brain.mcp_manager import mcp_manager


async def test_diagram_update():
    print("Testing devtools_update_architecture_diagrams...")
    try:
        # Call the tool via MCP Manager (which should have it registered/loaded)
        # Note: We need to ensure devtools server is loaded. 
        # By default mcp_manager loads config. 
        # As we are running a script, we might need to rely on the server being running or mcp_manager starting it.
        # But for this test, let's try calling it.
        
        result = await mcp_manager.call_tool(
            "devtools",
            "devtools_update_architecture_diagrams",
            {
                "target_mode": "internal",
                "use_reasoning": False # Faster for test
            }
        )
        print("Result:", result)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_diagram_update())
