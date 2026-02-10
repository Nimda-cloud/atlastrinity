#!/usr/bin/env python3
"""
Quick Real-Time Test for Essential macOS Use MCP Tools
Tests the most important tools with actual usage scenarios
"""

import asyncio
import json
import os
import time

BINARY_PATH = "vendor/mcp-server-macos-use/mcp-server-macos-use"

# Essential tools to test (excluding problematic ones)
ESSENTIAL_TOOLS = [
    ("macos-use_get_time", "Get current system time"),
    ("macos-use_get_system_info", "Get system information"),
    ("macos-use_get_battery_info", "Get battery status"),
    ("macos-use_list_running_apps", "List running applications"),
    ("macos-use_get_clipboard", "Get clipboard content"),
    ("macos-use_set_clipboard", "Set clipboard content"),
    ("macos-use_fetch_url", "Fetch URL content"),
    ("macos-use_run_applescript", "Run AppleScript"),
    ("macos-use_show_notification", "Show system notification"),
    ("macos-use_speak_text", "Text-to-speech"),
]


async def test_single_tool(tool_name, test_args=None):
    """Test a single tool quickly"""
    print(f"🧪 {tool_name}...", end=" ")

    process = await asyncio.create_subprocess_exec(
        BINARY_PATH,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    if not all([process.stdin, process.stdout, process.stderr]):
        print("❌ Failed to start process")
        return False

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
        tool_call = {"name": tool_name, "arguments": test_args or {}}

        call_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": tool_call}

        start_time = time.time()
        process.stdin.write(json.dumps(call_msg).encode() + b"\n")
        await process.stdin.drain()

        # Wait for response with timeout
        line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
        resp = json.loads(line.decode())
        elapsed = time.time() - start_time

        if resp.get("id") == 2:
            if "error" in resp:
                print(f"❌ {resp['error']}")
                return False
            print(f"✅ ({elapsed:.2f}s)")
            return True

    except TimeoutError:
        print("⏰ Timeout")
        return False
    except Exception as e:
        print(f"❌ {str(e)[:50]}")
        return False
    finally:
        process.terminate()
        await process.wait()

    return False


async def main():
    if not os.path.exists(BINARY_PATH):
        print(f"❌ Binary not found at {BINARY_PATH}")
        return

    print("🚀 Quick macOS Use MCP Tools Test")
    print("=" * 50)

    success_count = 0
    total_count = len(ESSENTIAL_TOOLS)

    for tool_name, description in ESSENTIAL_TOOLS:
        print(f"\n📝 {description}")

        # Prepare test arguments
        test_args = {}
        if tool_name == "macos-use_fetch_url":
            test_args = {"url": "https://example.com"}
        elif tool_name == "macos-use_set_clipboard":
            test_args = {"text": "Test content from MCP"}
        elif tool_name == "macos-use_run_applescript":
            test_args = {"script": 'return "AppleScript test successful"'}
        elif tool_name == "macos-use_show_notification":
            test_args = {"title": "MCP Test", "message": "Testing notification"}
        elif tool_name == "macos-use_speak_text":
            test_args = {"text": "Test speech"}

        if await test_single_tool(tool_name, test_args):
            success_count += 1

    print("\n" + "=" * 50)
    print("📊 RESULTS")
    print("=" * 50)
    print(f"✅ Successful: {success_count}/{total_count}")
    print(f"❌ Failed: {total_count - success_count}/{total_count}")
    print(f"📈 Success Rate: {(success_count / total_count) * 100:.1f}%")

    if success_count == total_count:
        print("\n🎉 All essential tools working perfectly!")
    elif success_count >= total_count * 0.8:
        print("\n👍 Most tools working well!")
    else:
        print("\n⚠️  Some tools need attention")


if __name__ == "__main__":
    asyncio.run(main())
