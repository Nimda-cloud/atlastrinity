#!/usr/bin/env python3
"""
Quick Test for Working macOS Use MCP Tools
Tests only the 26 working tools for fast verification
"""

import asyncio
import json
import os
import time

BINARY_PATH = "vendor/mcp-server-macos-use/mcp-server-macos-use"

# Only the 26 working tools
WORKING_TOOLS = [
    # System Info (4)
    ("macos-use_get_time", {}, "Get current system time"),
    ("macos-use_list_running_apps", {}, "List running applications"),
    ("macos-use_list_all_windows", {}, "List all windows"),
    ("macos-use_list_tools_dynamic", {}, "List all tools dynamically"),
    # Clipboard (2)
    ("macos-use_get_clipboard", {}, "Get clipboard content"),
    ("macos-use_set_clipboard", {"text": "Quick MCP Test"}, "Set clipboard content"),
    # Screen Analysis (3)
    ("macos-use_analyze_screen", {}, "Analyze screen content"),
    ("ocr", {}, "OCR alias"),
    ("analyze", {}, "Analyze alias"),
    # Network (1)
    ("macos-use_fetch_url", {"url": "https://httpbin.org/json"}, "Fetch JSON from URL"),
    # Mail (1)
    ("macos-use_mail_read_inbox", {"limit": 1}, "Read mail inbox"),
    # AppleScript (1)
    ("macos-use_run_applescript", {"script": 'return "Quick test successful"'}, "Run AppleScript"),
    # Notifications (1)
    (
        "macos-use_send_notification",
        {"title": "Quick MCP Test", "message": "Testing working tools"},
        "Show notification",
    ),
    # Window Management (1)
    ("macos-use_window_management", {"action": "list"}, "Window management"),
    # Search (1)
    ("macos-use_spotlight_search", {"query": "MCP"}, "Spotlight search"),
    # Interface Control (8)
    ("macos-use_click_and_traverse", {"x": 100, "y": 100}, "Click and traverse"),
    ("macos-use_double_click_and_traverse", {"x": 100, "y": 100}, "Double click and traverse"),
    ("macos-use_right_click_and_traverse", {"x": 100, "y": 100}, "Right click and traverse"),
    ("macos-use_type_and_traverse", {"text": "test"}, "Type and traverse"),
    ("macos-use_press_key_and_traverse", {"keyName": "return"}, "Press key and traverse"),
    ("macos-use_scroll_and_traverse", {"direction": "down", "amount": 1}, "Scroll and traverse"),
    ("macos-use_refresh_traversal", {}, "Refresh traversal"),
    (
        "macos-use_open_application_and_traverse",
        {"identifier": "com.apple.TextEdit"},
        "Open app and traverse",
    ),
    # System Commands (2)
    ("execute_command", {"command": "echo 'Quick MCP Test'"}, "Execute system command"),
    ("terminal", {"command": "echo 'Terminal Test'"}, "Terminal command"),
]


async def execute_tool(tool_name, args, description):
    """Execute a single tool and return result"""
    print(f"\n🔧 [{tool_name}] {description}")
    print(f"📝 Args: {args}")

    process = await asyncio.create_subprocess_exec(
        BINARY_PATH,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    if not all([process.stdin, process.stdout, process.stderr]):
        return {"status": "error", "message": "Failed to start process"}

    try:
        # Initialize
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        }

        process.stdin.write(json.dumps(init_msg).encode() + b"\n")
        await process.stdin.drain()

        # Wait for init response
        line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
        resp = json.loads(line.decode())

        # Send initialized notification
        init_notify = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        process.stdin.write(json.dumps(init_notify).encode() + b"\n")
        await process.stdin.drain()

        # Call tool
        tool_call = {"name": tool_name, "arguments": args}

        call_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": tool_call}

        start_time = time.time()
        process.stdin.write(json.dumps(call_msg).encode() + b"\n")
        await process.stdin.drain()

        # Wait for response with shorter timeout for quick test
        timeout = 10.0
        line = await asyncio.wait_for(process.stdout.readline(), timeout=timeout)
        resp = json.loads(line.decode())
        elapsed = time.time() - start_time

        if resp.get("id") == 2:
            if "error" in resp:
                print(f"❌ Error: {resp['error']}")
                return {"status": "error", "message": resp["error"], "time": elapsed}
            content = resp["result"].get("content", [])
            if content:
                text = content[0].get("text", "")
                # Truncate long responses
                display_text = text[:100] + "..." if len(text) > 100 else text
                print(f"✅ Success ({elapsed:.2f}s): {display_text}")
                return {"status": "success", "message": display_text, "time": elapsed}
            print(f"✅ Success ({elapsed:.2f}s): No content returned")
            return {"status": "success", "message": "No content", "time": elapsed}

    except TimeoutError:
        print(f"⏰ Timeout after {timeout}s")
        return {"status": "timeout", "message": f"Timeout after {timeout}s"}
    except Exception as e:
        print(f"❌ Exception: {str(e)[:100]}")
        return {"status": "error", "message": str(e)}
    finally:
        process.terminate()
        await process.wait()


async def main():
    if not os.path.exists(BINARY_PATH):
        print(f"❌ Binary not found at {BINARY_PATH}")
        return

    print("🚀 QUICK Test for Working macOS Use Tools")
    print("=" * 60)
    print(f"Testing {len(WORKING_TOOLS)} confirmed working tools")

    results = {"success": 0, "error": 0, "timeout": 0, "total": len(WORKING_TOOLS)}

    start_time = time.time()

    for i, (tool_name, args, description) in enumerate(WORKING_TOOLS, 1):
        print(f"\n{'=' * 20} [{i}/{len(WORKING_TOOLS)}] {'=' * 20}")

        result = await execute_tool(tool_name, args, description)
        results[result["status"]] += 1

        # Small delay between operations
        await asyncio.sleep(0.2)

    total_time = time.time() - start_time

    print("\n" + "=" * 60)
    print("📊 QUICK TEST RESULTS")
    print("=" * 60)
    print(f"✅ Successful: {results['success']}/{results['total']}")
    print(f"❌ Errors: {results['error']}/{results['total']}")
    print(f"⏰ Timeouts: {results['timeout']}/{results['total']}")
    print(f"⏱️  Total Time: {total_time:.1f} seconds")
    print(f"📈 Success Rate: {(results['success'] / results['total']) * 100:.1f}%")

    if results["success"] >= results["total"] * 0.9:
        print("\n🎉 EXCELLENT! Most working tools confirmed!")
    elif results["success"] >= results["total"] * 0.7:
        print("\n👍 GOOD! Majority of working tools confirmed!")
    else:
        print("\n⚠️  Some working tools having issues")

    print(f"\n📋 Confirmed Working: {results['success']}/{len(WORKING_TOOLS)}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
