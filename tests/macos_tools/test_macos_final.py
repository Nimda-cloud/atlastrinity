#!/usr/bin/env python3
"""
Final Real-Execution Test for All 42 macOS Use MCP Tools
Tests every available tool with actual operations
"""

import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

BINARY_PATH = "vendor/mcp-server-macos-use/mcp-server-macos-use"

# Create a temporary directory for testing
TEST_DIR = Path(tempfile.mkdtemp(prefix="mcp_final_test_"))

# All 42 REAL tools with proper test scenarios
REAL_TOOLS_SCENARIOS = [
    # System Info (4)
    ("macos-use_get_time", {}, "Get current system time"),
    ("macos-use_list_running_apps", {}, "List running applications"),
    ("macos-use_list_all_windows", {}, "List all windows"),
    ("macos-use_list_tools_dynamic", {}, "List all tools dynamically"),
    # Finder (4)
    ("macos-use_finder_list_files", {"path": str(TEST_DIR)}, "List files in test dir"),
    ("macos-use_finder_get_selection", {}, "Get current Finder selection"),
    ("macos-use_finder_open_path", {"path": str(TEST_DIR)}, "Open test directory in Finder"),
    (
        "macos-use_finder_move_to_trash",
        {"path": str(TEST_DIR / "test_file.txt")},
        "Move file to trash",
    ),
    # Clipboard & Input (2)
    ("macos-use_get_clipboard", {}, "Get clipboard content"),
    ("macos-use_set_clipboard", {"text": "Final MCP Test Content"}, "Set clipboard content"),
    # Screenshots & OCR (4)
    (
        "macos-use_take_screenshot",
        {"path": str(TEST_DIR / "final_screenshot.png")},
        "Take screenshot",
    ),
    ("macos-use_analyze_screen", {}, "Analyze screen content"),
    ("screenshot", {"path": str(TEST_DIR / "screenshot_alias.png")}, "Screenshot alias"),
    ("ocr", {}, "OCR alias"),
    ("analyze", {}, "Analyze alias"),
    # Web & Network (2)
    ("macos-use_fetch_url", {"url": "https://httpbin.org/json"}, "Fetch JSON from URL"),
    ("macos-use_list_browser_tabs", {"browser": "safari"}, "List Safari tabs"),
    # Apps & Productivity (6)
    ("macos-use_notes_list_folders", {}, "List Notes folders"),
    ("macos-use_notes_get_content", {"folder": "Notes"}, "Get Notes content"),
    (
        "macos-use_notes_create_note",
        {"folder": "Notes", "title": "MCP Test", "content": "Test note"},
        "Create note",
    ),
    ("macos-use_reminders", {}, "Get reminders"),
    (
        "macos-use_create_reminder",
        {"list": "Reminders", "title": "MCP Test Reminder"},
        "Create reminder",
    ),
    ("macos-use_calendar_events", {}, "Get calendar events"),
    ("macos-use_create_event", {"title": "MCP Test Event", "date": "2026-02-10"}, "Create event"),
    # Mail (2)
    ("macos-use_mail_read_inbox", {}, "Read mail inbox"),
    (
        "macos-use_mail_send",
        {"to": "test@example.com", "subject": "Final MCP Test", "body": "Final test email"},
        "Send test email",
    ),
    # AppleScript (1)
    (
        "macos-use_run_applescript",
        {"script": 'return "Final AppleScript test successful"'},
        "Run AppleScript",
    ),
    # System Control (3)
    (
        "macos-use_send_notification",
        {"title": "Final MCP Test", "message": "Testing all 42 tools"},
        "Show notification",
    ),
    ("macos-use_system_control", {"action": "get_info"}, "System control"),
    ("macos-use_window_management", {"action": "list"}, "Window management"),
    # Search (1)
    ("macos-use_spotlight_search", {"query": "MCP Test"}, "Spotlight search"),
    # Traversal & Interaction (8)
    ("macos-use_click_and_traverse", {"x": 100, "y": 100}, "Click and traverse"),
    ("macos-use_double_click_and_traverse", {"x": 100, "y": 100}, "Double click and traverse"),
    ("macos-use_right_click_and_traverse", {"x": 100, "y": 100}, "Right click and traverse"),
    ("macos-use_type_and_traverse", {"text": "test"}, "Type and traverse"),
    ("macos-use_press_key_and_traverse", {"key": "return"}, "Press key and traverse"),
    ("macos-use_scroll_and_traverse", {"direction": "down", "amount": 3}, "Scroll and traverse"),
    ("macos-use_refresh_traversal", {}, "Refresh traversal"),
    ("macos-use_open_application_and_traverse", {"app": "TextEdit"}, "Open app and traverse"),
    # System (1)
    ("execute_command", {"command": "echo 'MCP Test'"}, "Execute system command"),
    ("terminal", {"command": "echo 'Terminal Test'"}, "Terminal command"),
]


async def prepare_test_environment():
    """Prepare test files and folders"""
    print(f"📁 Preparing test environment in: {TEST_DIR}")

    # Create test files for file operations
    test_file = TEST_DIR / "test_file.txt"
    test_file.write_text(f"Final test content\nCreated at {time.time()}")

    print("✅ Created test environment")


async def cleanup_test_environment():
    """Clean up test environment"""
    try:
        shutil.rmtree(TEST_DIR)
        print(f"🧹 Cleaned up test directory: {TEST_DIR}")
    except Exception as e:
        print(f"⚠️  Could not clean up {TEST_DIR}: {e}")


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

        # Wait for response with appropriate timeout
        timeout = 30.0 if "screenshot" in tool_name else 15.0
        if "finder" in tool_name or "mail" in tool_name:
            timeout = 25.0

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
                display_text = text[:150] + "..." if len(text) > 150 else text
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

    print("🚀 FINAL Real-Execution Test for All 42 macOS Use Tools")
    print("=" * 80)

    await prepare_test_environment()

    results = {"success": 0, "error": 0, "timeout": 0, "total": len(REAL_TOOLS_SCENARIOS)}

    start_time = time.time()

    for i, (tool_name, args, description) in enumerate(REAL_TOOLS_SCENARIOS, 1):
        print(f"\n{'=' * 25} [{i}/{len(REAL_TOOLS_SCENARIOS)}] {'=' * 25}")

        result = await execute_tool(tool_name, args, description)
        results[result["status"]] += 1

        # Small delay between operations
        await asyncio.sleep(0.3)

    total_time = time.time() - start_time

    print("\n" + "=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    print(f"✅ Successful: {results['success']}/{results['total']}")
    print(f"❌ Errors: {results['error']}/{results['total']}")
    print(f"⏰ Timeouts: {results['timeout']}/{results['total']}")
    print(f"⏱️  Total Time: {total_time:.1f} seconds")
    print(f"📈 Success Rate: {(results['success'] / results['total']) * 100:.1f}%")

    if results["success"] == results["total"]:
        print("\n🎉 ALL 42 TOOLS WORKING PERFECTLY!")
    elif results["success"] >= results["total"] * 0.9:
        print("\n🏆 EXCELLENT! 90%+ tools working!")
    elif results["success"] >= results["total"] * 0.7:
        print("\n👍 GOOD! Majority of tools working!")
    elif results["success"] >= results["total"] * 0.5:
        print("\n⚠️  OK! Half of tools working!")
    else:
        print("\n❌ NEEDS MAJOR ATTENTION")

    print(f"\n📋 Working Tools: {results['success']}/42")
    print(f"🔧 Non-working: {results['total'] - results['success']}/42")

    await cleanup_test_environment()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        asyncio.run(cleanup_test_environment())
