#!/usr/bin/env python3
"""
Test All 46 macOS Use MCP Tools
Comprehensive testing of every tool
"""

import asyncio
import json
import sys
from datetime import datetime

sys.path.append("src")
from brain.mcp_manager import MCPManager


async def test_all_tools():
    manager = MCPManager()

    print("🚀 ТЕСТУВАННЯ ВСІХ 46 ІНСТРУМЕНТІВ")
    print("=" * 80)

    # Get all tools
    tools = await manager.list_tools("macos-use")
    print(f"📊 Загальна кількість інструментів: {len(tools)}")

    success_count = 0
    error_count = 0
    tested_tools = []

    # Test each tool with basic parameters
    for i, tool in enumerate(tools, 1):
        name = tool.name if hasattr(tool, "name") else str(tool)
        desc = tool.description if hasattr(tool, "description") else "No description"

        print(f"\n{i:2d}. {name}")
        print(f"    {desc[:80]}...")

        try:
            # Test based on tool type
            if "open_application" in name:
                result = await manager.call_tool(
                    "macos-use", name, {"identifier": "com.apple.finder"}
                )
            elif "click" in name or "right_click" in name or "double_click" in name:
                result = await manager.call_tool("macos-use", name, {"x": 100, "y": 100})
            elif "drag_and_drop" in name:
                result = await manager.call_tool(
                    "macos-use", name, {"startX": 100, "startY": 100, "endX": 200, "endY": 200}
                )
            elif "type" in name:
                result = await manager.call_tool("macos-use", name, {"text": "Test typing"})
            elif "press_key" in name:
                result = await manager.call_tool("macos-use", name, {"keyName": "Return"})
            elif "scroll" in name:
                result = await manager.call_tool(
                    "macos-use", name, {"direction": "down", "amount": 3}
                )
            elif "refresh" in name:
                result = await manager.call_tool("macos-use", name, {})
            elif "window_management" in name:
                result = await manager.call_tool("macos-use", name, {"action": "make_front"})
            elif "execute_command" in name or "terminal" in name:
                result = await manager.call_tool(
                    "macos-use", name, {"command": 'echo "Hello World"'}
                )
            elif "screenshot" in name or name in ["screenshot", "ocr", "analyze"]:
                result = await manager.call_tool(
                    "macos-use", name, {"path": f"/tmp/test_{name}.png"}
                )
            elif "set_clipboard" in name:
                result = await manager.call_tool(
                    "macos-use", name, {"text": "Test clipboard content"}
                )
            elif "get_clipboard" in name:
                result = await manager.call_tool("macos-use", name, {})
            elif "clipboard_history" in name:
                result = await manager.call_tool("macos-use", name, {"limit": 5})
            elif "system_control" in name:
                result = await manager.call_tool("macos-use", name, {"action": "get_info"})
            elif "fetch_url" in name:
                result = await manager.call_tool(
                    "macos-use", name, {"url": "https://httpbin.org/json"}
                )
            elif "get_time" in name:
                result = await manager.call_tool("macos-use", name, {"format": "readable"})
            elif "countdown_timer" in name:
                result = await manager.call_tool(
                    "macos-use", name, {"seconds": 1, "message": "Test countdown"}
                )
            elif "run_applescript" in name:
                result = await manager.call_tool(
                    "macos-use",
                    name,
                    {"script": 'tell application "Finder" to get name of startup disk'},
                )
            elif "applescript_templates" in name:
                result = await manager.call_tool("macos-use", name, {"list": True})
            elif "calendar_events" in name:
                result = await manager.call_tool(
                    "macos-use",
                    name,
                    {"start": "2026-02-10T00:00:00Z", "end": "2026-02-10T23:59:59Z"},
                )
            elif "create_event" in name:
                result = await manager.call_tool(
                    "macos-use", name, {"title": "Test Event", "date": "2026-02-10T15:00:00Z"}
                )
            elif "reminders" in name:
                result = await manager.call_tool("macos-use", name, {})
            elif "create_reminder" in name:
                result = await manager.call_tool("macos-use", name, {"title": "Test Reminder"})
            elif "spotlight_search" in name:
                result = await manager.call_tool("macos-use", name, {"query": "test"})
            elif "send_notification" in name:
                result = await manager.call_tool(
                    "macos-use", name, {"title": "Test Notification", "message": "This is a test"}
                )
            elif "notification_schedule" in name:
                result = await manager.call_tool("macos-use", name, {"list": True})
            elif "notes_list_folders" in name:
                result = await manager.call_tool("macos-use", name, {})
            elif "notes_create_note" in name:
                result = await manager.call_tool("macos-use", name, {"body": "Test note content"})
            elif "notes_get_content" in name:
                result = await manager.call_tool("macos-use", name, {"name": "Test Note"})
            elif "mail_send" in name:
                result = await manager.call_tool(
                    "macos-use",
                    name,
                    {
                        "to": "test@example.com",
                        "subject": "Test Email",
                        "body": "Test email body",
                        "draft": True,
                    },
                )
            elif "mail_read_inbox" in name:
                result = await manager.call_tool("macos-use", name, {"limit": 3})
            elif "finder_list_files" in name:
                result = await manager.call_tool("macos-use", name, {"path": "/tmp", "limit": 5})
            elif "finder_get_selection" in name:
                result = await manager.call_tool("macos-use", name, {})
            elif "finder_open_path" in name:
                result = await manager.call_tool("macos-use", name, {"path": "/tmp"})
            elif "finder_move_to_trash" in name:
                result = await manager.call_tool("macos-use", name, {"path": "/tmp/test_file.txt"})
            elif "list_running_apps" in name:
                result = await manager.call_tool("macos-use", name, {})
            elif "list_browser_tabs" in name:
                result = await manager.call_tool("macos-use", name, {"browser": "Safari"})
            elif "list_all_windows" in name or "list_tools_dynamic" in name:
                result = await manager.call_tool("macos-use", name, {})
            else:
                # Default test for unknown tools
                result = await manager.call_tool("macos-use", name, {})

            # Check result
            if result and hasattr(result, "content") and result.content:
                content = result.content[0].text if result.content else ""
                is_error = result.isError if hasattr(result, "isError") else False

                if is_error:
                    print(f"    ❌ Помилка: {content[:100]}...")
                    error_count += 1
                else:
                    print(f"    ✅ Успішно: {content[:100]}...")
                    success_count += 1
                    tested_tools.append(
                        {"name": name, "status": "success", "result": content[:100]}
                    )
            else:
                print("    ❌ Немає відповіді")
                error_count += 1

        except Exception as e:
            print(f"    ❌ Помилка виконання: {str(e)[:100]}...")
            error_count += 1

    # Final summary
    print("\n" + "=" * 80)
    print("🎉 ТЕСТУВАННЯ ВСІХ ІНСТРУМЕНТІВ ЗАВЕРШЕНО!")
    print("=" * 80)

    print("\n📊 РЕЗУЛЬТАТИ ТЕСТУВАННЯ:")
    print(f"✅ Успішних тестів: {success_count}")
    print(f"❌ Помилок: {error_count}")
    print(f"📈 Загальна кількість інструментів: {len(tools)}")

    success_rate = (success_count / len(tools)) * 100 if len(tools) > 0 else 0
    print(f"🎯 Рівень успішності: {success_rate:.1f}%")

    print("\n🏆 ФІНАЛЬНИЙ СТАТУС:")
    if success_rate >= 95:
        print("🟢 ВІДМІННО! Усі інструменти працюють ідеально!")
    elif success_rate >= 90:
        print("🟡 ДОБРЕ! Більшість інструментів працюють добре!")
    elif success_rate >= 80:
        print("🟠 ЗАДОВІЛЬНО! Потрібні деякі покращення!")
    else:
        print("🔴 ПОТРІБНО ПОКРАЩЕННЯ!")

    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_tools": len(tools),
        "success_count": success_count,
        "error_count": error_count,
        "success_rate": success_rate,
        "tested_tools": tested_tools,
    }

    with open("/tmp/macos_tools_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n📄 Результати збережено в: /tmp/macos_tools_test_results.json")

    return results


asyncio.run(test_all_tools())
