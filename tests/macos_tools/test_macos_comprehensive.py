# ruff: noqa: T201
#!/usr/bin/env python3
"""
Comprehensive Real-Time Test for all macOS Use MCP Tools
Tests all 42 tools with actual usage scenarios
"""

import asyncio
import json
import os
import time

BINARY_PATH = "vendor/mcp-server-macos-use/mcp-server-macos-use"

# All 42 tools organized by category
TOOLS_BY_CATEGORY = {
    "System Info": [
        "macos-use_get_time",
        "macos-use_get_system_info",
        "macos-use_get_battery_info",
        "macos-use_list_running_apps",
        "macos-use_list_all_windows",
    ],
    "Finder": [
        "macos-use_finder_list_files",
        "macos-use_finder_get_selection",
        "macos-use_finder_open_path",
        "macos-use_finder_move_to_trash",
    ],
    "Clipboard & Input": [
        "macos-use_get_clipboard",
        "macos-use_set_clipboard",
        "macos-use_type_text",
        "macos-use_press_key",
    ],
    "Screenshots & OCR": [
        "macos-use_take_screenshot",
        "macos-use_analyze_screen",
        "screenshot",  # alias
        "ocr",  # alias
        "analyze",  # alias
    ],
    "Web & Network": ["macos-use_fetch_url", "macos-use_list_browser_tabs"],
    "Apps & Productivity": [
        "macos-use_notes_list_folders",
        "macos-use_reminders",
        "macos-use_calendar_events",
        "macos-use_mail_read_inbox",
        "macos-use_mail_send",
    ],
    "AppleScript": ["macos-use_run_applescript", "macos-use_run_javascript"],
    "System Control": [
        "macos-use_open_app",
        "macos-use_close_app",
        "macos-use_set_volume",
        "macos-use_sleep_display",
    ],
    "Files & Folders": [
        "macos-use_create_folder",
        "macos-use_delete_file",
        "macos-use_move_file",
        "macos-use_copy_file",
    ],
    "Advanced": [
        "macos-use_list_tools_dynamic",
        "macos-use_get_app_path",
        "macos-use_show_notification",
        "macos-use_speak_text",
    ],
}


async def read_stream(stream):
    while True:
        line = await stream.readline()
        if not line:
            break
        yield line


async def test_tool(tool_name, description=""):
    """Test a single tool and return result"""
    print(f"\n🧪 Testing: {tool_name}")
    if description:
        print(f"📝 Purpose: {description}")

    process = await asyncio.create_subprocess_exec(
        BINARY_PATH,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    if not all([process.stdin, process.stdout, process.stderr]):
        return {"status": "error", "message": "Failed to create subprocess"}

    request_id = 1

    # Initialize
    init_msg = {
        "jsonrpc": "2.0",
        "id": request_id,
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
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        try:
            resp = json.loads(line.decode())
            if resp.get("id") == request_id:
                break
        except:
            continue

    # Send initialized notification
    init_notify = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    process.stdin.write(json.dumps(init_notify).encode() + b"\n")
    await process.stdin.drain()

    # Prepare tool call with appropriate arguments
    tool_call = await prepare_tool_call(tool_name)
    request_id += 1

    call_msg = {"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": tool_call}

    start_time = time.time()
    process.stdin.write(json.dumps(call_msg).encode() + b"\n")
    await process.stdin.drain()

    # Wait for response
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        try:
            resp = json.loads(line.decode())
            if resp.get("id") == request_id:
                elapsed = time.time() - start_time
                process.terminate()

                if "error" in resp:
                    return {"status": "error", "message": resp["error"], "time": elapsed}
                content = resp["result"].get("content", [])
                if content:
                    text = content[0].get("text", "")
                    return {
                        "status": "success",
                        "message": text[:200] + "..." if len(text) > 200 else text,
                        "time": elapsed,
                    }
                return {"status": "success", "message": "No content returned", "time": elapsed}
        except:
            continue

    process.terminate()
    return {"status": "timeout", "message": "No response received"}


async def prepare_tool_call(tool_name):
    """Prepare appropriate arguments for each tool"""
    base_call = {"name": tool_name, "arguments": {}}

    # Add appropriate arguments based on tool
    if tool_name == "macos-use_fetch_url":
        base_call["arguments"] = {"url": "https://example.com"}
    elif tool_name == "macos-use_set_clipboard":
        base_call["arguments"] = {"text": "Test clipboard content"}
    elif tool_name == "macos-use_type_text":
        base_call["arguments"] = {"text": "test"}
    elif tool_name == "macos-use_press_key":
        base_call["arguments"] = {"key": "return"}
    elif tool_name in {"macos-use_finder_open_path", "macos-use_finder_list_files"}:
        base_call["arguments"] = {"path": "/tmp"}
    elif tool_name == "macos-use_create_folder":
        base_call["arguments"] = {"path": "/tmp/test_mcp_folder"}
    elif tool_name == "macos-use_open_app":
        base_call["arguments"] = {"app": "TextEdit"}
    elif tool_name == "macos-use_set_volume":
        base_call["arguments"] = {"volume": 50}
    elif tool_name == "macos-use_run_applescript":
        base_call["arguments"] = {"script": 'return "Hello from AppleScript"'}
    elif tool_name == "macos-use_run_javascript":
        base_call["arguments"] = {"script": 'return "Hello from JavaScript"'}
    elif tool_name == "macos-use_show_notification":
        base_call["arguments"] = {"title": "MCP Test", "message": "Testing notification"}
    elif tool_name == "macos-use_speak_text":
        base_call["arguments"] = {"text": "Test speech"}
    elif tool_name == "macos-use_mail_send":
        base_call["arguments"] = {"to": "test@example.com", "subject": "Test", "body": "Test email"}
    elif tool_name == "macos-use_list_browser_tabs":
        base_call["arguments"] = {"browser": "safari"}

    return base_call


async def main():
    if not os.path.exists(BINARY_PATH):
        print(f"❌ Binary not found at {BINARY_PATH}")
        return

    print("🚀 Starting Comprehensive macOS Use MCP Tools Test")
    print("=" * 60)

    results = {}
    total_tools = sum(len(tools) for tools in TOOLS_BY_CATEGORY.values())
    tested_count = 0

    for category, tools in TOOLS_BY_CATEGORY.items():
        print(f"\n📂 Category: {category}")
        print("-" * 40)

        category_results = {}
        for tool in tools:
            tested_count += 1
            print(f"[{tested_count}/{total_tools}] ", end="")

            result = await test_tool(tool)
            category_results[tool] = result

            if result["status"] == "success":
                print(f"✅ {tool} ({result['time']:.2f}s)")
            elif result["status"] == "error":
                print(f"❌ {tool} - {result['message']}")
            else:
                print(f"⏰ {tool} - {result['message']}")

        results[category] = category_results

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    total_success = 0
    total_error = 0
    total_timeout = 0

    for category, tools in results.items():
        print(f"\n📂 {category}:")
        success = sum(1 for r in tools.values() if r["status"] == "success")
        error = sum(1 for r in tools.values() if r["status"] == "error")
        timeout = sum(1 for r in tools.values() if r["status"] == "timeout")

        total_success += success
        total_error += error
        total_timeout += timeout

        print(f"   ✅ Success: {success}")
        print(f"   ❌ Error: {error}")
        print(f"   ⏰ Timeout: {timeout}")

    print("\n🎯 OVERALL RESULTS:")
    print(f"   ✅ Successful: {total_success}/{total_tools}")
    print(f"   ❌ Errors: {total_error}/{total_tools}")
    print(f"   ⏰ Timeouts: {total_timeout}/{total_tools}")
    print(f"   📈 Success Rate: {(total_success / total_tools) * 100:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
