#!/usr/bin/env python3
"""
Verify Vibe Tools Integration
-----------------------------
This script connects to the Vibe MCP server and asks it to list its available tools,
specifically checking for xcodebuild and devtools integration.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("verify_vibe")

from src.brain.mcp_manager import MCPManager

async def verify_vibe_capabilities():
    """Connect to Vibe and query its capabilities."""
    manager = MCPManager()
    
    # Only connect to Vibe for this test
    # We need to manually initialize the manager's config to avoid connecting to everything
    # But for now, let's just use the standard connect method but request specific interaction
    
    logger.info("Connecting to Vibe server...")
    # Connect specifically to Vibe
    session = await manager.get_session("vibe")
    
    if not session:
        logger.error("❌ Failed to connect to Vibe server!")
        return
        
    logger.info("✅ Connected to Vibe.")
    
    # We don't need 'results' dict anymore
    results = {"vibe": session}
    
    # Construct a prompt to ask Vibe about its tools
    prompt = """
    List all the tools you have available specifically related to:
    1. Xcode / iOS development (xcodebuild)
    2. Code Analysis / Linting (devtools)
    
    Do not use them, just list the tool names or detailed capabilities you see in your context.
    Format your response as a JSON object with keys 'xcode_tools' and 'devtools_tools' referencing the tool names you found.
    """
    
    logger.info("Listing tools directly from Vibe session...")
    try:
        tools_result = await session.list_tools()
        vibe_tools = tools_result.tools
        logger.info(f"Vibe Server exposes {len(vibe_tools)} tools.")
        for t in vibe_tools:
            logger.info(f" - {t.name}")
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        vibe_tools = []

    # We want to use 'vibe_prompt' or 'vibe_ask' to interact with the agent inside
    target_tool = "vibe_prompt"
    # Basic check if we found it in the list (if listing succeeded)
    if vibe_tools and not any(t.name == target_tool for t in vibe_tools):
        target_tool = "vibe_ask" # Fallback
        
    logger.info(f"Using tool '{target_tool}' to query Vibe Agent...")
    
    try:
        # Execute the tool
        result = await manager.call_tool(
            server_name="vibe",
            tool_name=target_tool,
            arguments={"prompt": prompt}
        )
        
        if result.isError:
            # Try to extract text from error content if available
            error_text = ""
            if hasattr(result, 'content') and result.content:
                error_text = "".join([c.text for c in result.content if hasattr(c, 'text')])
            logger.error(f"❌ Vibe returned error. Text: {error_text}")
        else:
            logger.info("✅ Vibe responded!")
            
            # Extract text from content list
            response_text = ""
            if hasattr(result, 'content') and result.content:
                response_text = "".join([c.text for c in result.content if hasattr(c, 'text')])
                
            print("\n=== VIBE RESPONSE ===\n")
            print(response_text)
            print("\n=====================\n")
            
            # Simple keyword check
            lower_text = response_text.lower()
            if "xcode" in lower_text or "build" in lower_text:
                logger.info("✅ Vibe mentions Xcode capabilities.")
            else:
                logger.warning("⚠️ Vibe did NOT mention Xcode capabilities clearly.")
                
            if "lint" in lower_text or "analysis" in lower_text or "ruff" in lower_text:
                logger.info("✅ Vibe mentions DevTools/Linting capabilities.")
            else:
                logger.warning("⚠️ Vibe did NOT mention DevTools capabilities clearly.")

    except Exception as e:
        logger.error(f"❌ Exception during tool call: {e}")
    finally:
        await manager.cleanup()

if __name__ == "__main__":
    asyncio.run(verify_vibe_capabilities())
