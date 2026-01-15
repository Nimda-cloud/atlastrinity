
import asyncio
import os
import sys
import json
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.brain.mcp_manager import mcp_manager
from src.brain.logger import logger

async def test_tools():
    logger.info("🧪 Starting COMPREHENSIVE test of all macOS Native tools...")
    
    # Initialize MCP Manager (it will use the config to find the server)
    # Note: We need to make sure the server path in config is correct.
    # Usually it points to the release build we just made.
    
    SERVER = "macos-use"
    
    try:
        # 1. List Tools
        tools = await mcp_manager.list_tools(SERVER)
        logger.info(f"✅ Tools available: {[t.name for t in tools]}")
        
        # 2. Test execute_command
        logger.info("Testing execute_command (alias terminal)...")
        res = await mcp_manager.call_tool(SERVER, "execute_command", {"command": "uptime"})
        logger.info(f"Result: {res.content[0].text if hasattr(res, 'content') else res}")

        # 3. Test Clipboard
        logger.info("Testing Clipboard (set/get)...")
        test_text = "Trinity-Test-123"
        await mcp_manager.call_tool(SERVER, "macos-use_set_clipboard", {"text": test_text})
        get_res = await mcp_manager.call_tool(SERVER, "macos-use_get_clipboard", {})
        clipboard_val = get_res.content[0].text if hasattr(get_res, 'content') else ""
        if clipboard_val == test_text:
            logger.info(f"✅ Clipboard test PASSED: {clipboard_val}")
        else:
            logger.error(f"❌ Clipboard test FAILED: {clipboard_val}")

        # 4. Test Screenshot (JPEG)
        logger.info("Testing Screenshot...")
        screenshot_res = await mcp_manager.call_tool(SERVER, "macos-use_take_screenshot", {})
        if hasattr(screenshot_res, 'content') and len(screenshot_res.content) > 0:
            size_kb = len(screenshot_res.content[0].text) / 1024
            logger.info(f"✅ Screenshot test PASSED: Received {size_kb:.2f} KB JPEG base64")
        else:
            logger.error(f"❌ Screenshot test FAILED: {screenshot_res}")

        # 5. Test System Control
        logger.info("Testing System Control (volume_up)...")
        sys_res = await mcp_manager.call_tool(SERVER, "macos-use_system_control", {"action": "volume_up"})
        logger.info(f"Result: {sys_res.content[0].text if hasattr(sys_res, 'content') else sys_res}")

        # 6. Test App Launch & Window Management
        logger.info("Testing App Launch (TextEdit)...")
        open_res = await mcp_manager.call_tool(SERVER, "macos-use_open_application_and_traverse", {"identifier": "com.apple.TextEdit"})
        
        # Extract PID
        pid = None
        if isinstance(open_res, dict) and "openResult" in open_res:
            pid = open_res["openResult"].get("pid")
        elif hasattr(open_res, 'content'):
            text = open_res.content[0].text
            try:
                data = json.loads(text)
                pid = data.get("traversalPid")
            except: pass
        
        if pid:
            logger.info(f"✅ App launched with PID: {pid}")
            
            # Move Window
            logger.info(f"Testing Window Management (move) for PID {pid}...")
            move_res = await mcp_manager.call_tool(SERVER, "macos-use_window_management", {"pid": pid, "action": "move", "x": 100, "y": 100})
            logger.info(f"Move Result: {move_res.content[0].text if hasattr(move_res, 'content') else move_res}")
            
            # Type text
            logger.info("Testing Typing...")
            await mcp_manager.call_tool(SERVER, "macos-use_type_and_traverse", {"pid": pid, "text": "Hello from Trinity!"})
            
            # Press Keys
            logger.info("Testing Key Press (Select All)...")
            await mcp_manager.call_tool(SERVER, "macos-use_press_key_and_traverse", {"pid": pid, "keyName": "a", "modifierFlags": ["command"]})
            
            # Scroll
            logger.info("Testing Scroll...")
            await mcp_manager.call_tool(SERVER, "macos-use_scroll_and_traverse", {"pid": pid, "direction": "down", "amount": 5})
            
            logger.info("✅ UI Interaction tests triggered.")
        else:
            logger.warning("⚠️ Could not extract PID, skipping UI tests.")

        # 7. Test Vision/OCR
        logger.info("Testing Vision/OCR...")
        ocr_res = await mcp_manager.call_tool(SERVER, "macos-use_analyze_screen", {})
        if hasattr(ocr_res, 'content') and len(ocr_res.content) > 0:
            logger.info(f"✅ Vision test PASSED: Received {len(ocr_res.content[0].text)} bytes of JSON results")
        else:
            logger.error(f"❌ Vision test FAILED: {ocr_res}")

    except Exception as e:
        logger.error(f"💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await mcp_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_tools())
