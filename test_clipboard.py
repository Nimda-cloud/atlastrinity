#!/usr/bin/env python3
"""Test clipboard functionality"""
import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

async def test_clipboard():
    from brain.mcp_manager import mcp_manager
    
    print("Testing clipboard tools...")
    
    # Test 1: Set clipboard
    print("\n1. Setting clipboard...")
    set_result = await mcp_manager.call_tool(
        'macos-use', 
        'macos-use_set_clipboard', 
        {'text': 'AtlasTrinity clipboard test 🚀'}
    )
    print(f"Set result: {set_result}")
    
    # Test 2: Get clipboard
    print("\n2. Getting clipboard...")
    get_result = await mcp_manager.call_tool(
        'macos-use', 
        'macos-use_get_clipboard', 
        {}
    )
    print(f"Get result: {get_result}")
    
    # Verify - MCP returns Pydantic objects, need to check content attribute
    if get_result:
        # Handle both dict and Pydantic object
        if hasattr(get_result, 'content'):
            content = get_result.content
        elif isinstance(get_result, dict):
            content = get_result.get('content', [])
        else:
            content = []
        
        if content and isinstance(content, list):
            for item in content:
                # Handle both dict and Pydantic TextContent
                if hasattr(item, 'text'):
                    text = item.text
                elif isinstance(item, dict):
                    text = item.get('text', '')
                else:
                    continue
                    
                if 'AtlasTrinity clipboard test' in text:
                    print("\n✅ Clipboard test PASSED!")
                    print(f"Clipboard content: {text}")
                    return True
    
    print("\n❌ Clipboard test FAILED!")
    print(f"Result type: {type(get_result)}")
    print(f"Result: {get_result}")
    return False

if __name__ == "__main__":
    asyncio.run(test_clipboard())
